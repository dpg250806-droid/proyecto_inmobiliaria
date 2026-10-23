import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from clustering_viviendas import kmeans
from cifras_control import prepare_summary_groups
from comparativo_fuentes import channel_summary, prepare, summary_table
from extraer_detalle_anuncios_revolico import (
    PATRONES_BANO,
    PATRONES_HABITACION,
    extraer_cantidad,
    procesar,
    slug_desde_url,
)
from integrar_fuentes import (
    aplicar_detalle_anuncios,
    aplicar_metadatos_revolico,
    aplicar_veredictos_revision,
    clasificar_tipo_vivienda,
    excluir_no_residenciales,
    parsear_fecha_exacta,
)
from revisar_precios_ausentes import (
    aplicar_politica_consulta,
    candidatos_de_texto,
    candidatos_de_url,
    resolver,
)
from procesar_entrevistas import QUESTIONS, build_coded, code_row, load_responses, prepare_frame
from convertir_precios_tasas import convertir, latest_rate_file
from extraer_metadatos_revolico import buscar_municipio_en_texto, parsear_pagina_anuncio
from integrar_fuentes import hogarencuba_source_path
from analisis_preguntas import rank_associations
from precio_moneda import detalle_analisis, extraer_precio_moneda, normalizar_moneda, parsear_importe, precios_analisis
from reprocesar_cubisima import reprocesar
from reprocesar_hogarencuba import latest_source, revalidar
from salidas import nueva_ruta_salida
from scraper_cubisima_online import (
    detectar_paginas,
    extraer_anuncios_pagina,
    extraer_datos_tarjeta,
    validar_respuesta,
)
from scraper_hogarencuba import detect_pages, list_links, parse_detail, run
from segmentacion_viviendas import build_segments, summary_table as segment_summary_table
from visualizaciones_fuentes import filtrar_municipios_por_fuente, money_labels


class PriceCurrencyParsingTests(unittest.TestCase):
    def test_european_euro_amount_and_cuc_url(self):
        text = "Anuncio 49.000,00 €"
        url = "https://example.test/casa-49000-cuc-en-habana.htm"
        self.assertEqual(extraer_precio_moneda(text, url), (49000.0, "CUC"))
        self.assertEqual(extraer_datos_tarjeta("casa de 2 cuartos", text, url)["moneda"], "CUC")

    def test_cubisima_parser_handles_half_bedrooms_and_page_cards(self):
        self.assertEqual(extraer_datos_tarjeta("Casa de 2½ cuartos", "", None)["habitaciones"], 2.5)
        self.assertEqual(extraer_datos_tarjeta("Casa de 2,5 cuartos", "", None)["habitaciones"], 2.5)
        html = """
        <div><h3>Casa de 2 cuartos</h3><span>Precio 49.000,00 €</span>
        <a href="/casas/casa-49000-cuc.htm">Ver más</a></div>
        """
        anuncios = extraer_anuncios_pagina(html, 3)
        self.assertEqual(len(anuncios), 1)
        self.assertEqual(anuncios[0]["moneda"], "CUC")
        self.assertEqual(anuncios[0]["pagina_origen"], 3)
        self.assertEqual(detectar_paginas("Página 1 de 27"), 27)
        self.assertEqual(detectar_paginas("P\uFFFDgina 1 de 25"), 25)
        self.assertEqual(detectar_paginas("P\u00C3\u00A1gina 1 de 25"), 25)

    def test_cubisima_response_rejects_block_pages_and_http_errors(self):
        class Response:
            status_code = 200
            text = "<html>Verify you are human</html>"

            def raise_for_status(self):
                return None

        with self.assertRaisesRegex(RuntimeError, "pagina de bloqueo"):
            validar_respuesta(Response(), "https://cubisima.test")

    def test_explicit_eur_and_usd_formats(self):
        self.assertEqual(extraer_precio_moneda("Precio € 5.000,00"), (5000.0, "EUR"))
        self.assertEqual(extraer_precio_moneda("Precio: $1,250"), (1250.0, "USD"))
        self.assertEqual(parsear_importe("1.250,50"), 1250.5)
        self.assertEqual(extraer_precio_moneda("Anuncio del 20/9/2026: 125.000,00 €"), (125000.0, "EUR"))
        self.assertEqual(extraer_precio_moneda("Precio 750 CUC"), (750.0, "CUC"))

    def test_unidentified_and_conflicting_currencies_are_not_guessed(self):
        self.assertEqual(extraer_precio_moneda("Precio 50.000"), (None, None))
        self.assertEqual(extraer_precio_moneda("Precio 50.000,00 â‚¬"), (None, None))
        self.assertEqual(extraer_precio_moneda("€ 5.000 y $ 5.000"), (None, None))
        self.assertEqual(extraer_precio_moneda("Sin precio"), (None, None))
        self.assertIsNone(normalizar_moneda("SIN_MONEDA"))

    def test_hogarencuba_requires_explicit_currency(self):
        usd = parse_detail(
            "Casa de 2 cuartos por $ 60.000 en La Habana",
            "HEC1 Casa por $ 60.000",
            "https://hogarencuba.test/HEC1",
        )
        eur = parse_detail(
            "Casa por € 49.000,00 en La Habana",
            "HEC2 Casa por € 49.000,00",
            "https://hogarencuba.test/HEC2",
        )
        unknown = parse_detail(
            '{"price":"50000"}',
            "HEC3 Casa de 2 cuartos",
            "https://hogarencuba.test/HEC3",
        )
        self.assertEqual((usd["precio_original"], usd["moneda"]), (60000.0, "USD"))
        self.assertEqual((eur["precio_original"], eur["moneda"]), (49000.0, "EUR"))
        self.assertEqual((unknown["precio_original"], unknown["moneda"]), (50000.0, None))

    def test_hogarencuba_parses_accented_fields_and_filters_external_links(self):
        links = list_links("""
        <a href="/HEC123">Casa de 2 cuartos</a>
        <a href="https://other.test/HEC999">Casa de 3 cuartos</a>
        """)
        self.assertEqual(links, [("https://hogarencuba.com/HEC123", "Casa de 2 cuartos")])
        self.assertEqual(
            detect_pages('<a href="/ventas/la-habana?page=10">10</a><a href="/HEC123">Casa</a>'),
            10,
        )
        parsed = parse_detail(
            "Superficie: 1.234,5 m², balcón y jardín",
            "Dúplex de 2 cuartos",
            "https://hogarencuba.com/HEC123",
        )
        self.assertEqual(parsed["superficie_m2"], 1234.5)
        self.assertEqual(parsed["tipo_vivienda"], "dúplex")
        self.assertEqual(parsed["habitaciones"], 2)
        self.assertEqual(parsed["balcon"], 1)
        self.assertEqual(parsed["jardin"], 1)
        self.assertEqual(parsed["ubicacion_raw"], "La Habana")

    def test_hogarencuba_uses_exact_jsonld_listing_and_explicit_currency_label(self):
        html = """
        <script type="application/ld+json">
        [
          {"@type":"Product","sku":"HEC123","name":"Casa anunciada",
           "offers":{"price":50000,"priceCurrency":"USD"}},
          {"@type":"Product","sku":"HEC999","name":"Anuncio recomendado",
           "offers":{"price":999999,"priceCurrency":"USD"}}
        ]
        </script>
        """
        parsed = parse_detail(
            "HEC123 Casa por $ 50.000 Descripción ampliada PRECIO EN EUR "
            "texto del anuncio Propiedades similares Casa por $999.999",
            "HEC123 Casa anunciada por $ 50.000",
            "https://hogarencuba.com/la-habana/HEC123-casa",
            html,
        )
        self.assertEqual(parsed["precio_original"], 50000)
        self.assertEqual(parsed["moneda"], "EUR")
        self.assertEqual(parsed["precio_metodo_extraccion"], "jsonld_identificador+etiqueta_precio")
        self.assertNotIn("999999", parsed["precio_evidencia"])
        no_price = parse_detail(
            "Descripción ampliada PRECIO EN EUR Precio ajustable",
            "HEC124 Casa",
            "https://hogarencuba.com/HEC124-casa",
        )
        self.assertIsNone(no_price["precio_original"])
        self.assertIsNone(no_price["moneda"])

    def test_hogarencuba_run_writes_one_complete_snapshot_without_network(self):
        listing = '<a href="/HEC123">Casa de 2 cuartos</a>'
        detail = "Casa por $ 60.000; 2 cuartos"

        def fake_fetch(url, timeout=30):
            return listing if url == "https://hogarencuba.com/ventas/la-habana" else detail

        with tempfile.TemporaryDirectory() as directory:
            with patch("scraper_hogarencuba.fetch", side_effect=fake_fetch), patch("scraper_hogarencuba.time.sleep"):
                frame = run(delay=0, output_dir=Path(directory))
            files = list(Path(directory).glob("*.csv"))
            self.assertEqual(len(frame), 1)
            self.assertEqual(len(files), 1)
            self.assertEqual(pd.read_csv(files[0]).loc[0, "moneda"], "USD")
            saved = pd.read_csv(files[0])
            self.assertTrue(saved.loc[0, "recoleccion_completa"])
            self.assertEqual(saved.loc[0, "fichas_fallidas"], 0)
            self.assertEqual(saved.loc[0, "paginas_total_detectadas"], 1)

    def test_hogarencuba_partial_page_limit_is_not_marked_complete(self):
        listing = (
            '<a href="/HEC123">Casa de 2 cuartos</a>'
            '<a href="/ventas/la-habana?page=2">2</a>'
        )

        def fake_fetch(url, timeout=30):
            return listing if url == "https://hogarencuba.com/ventas/la-habana" else "Casa por $ 60.000; 2 cuartos"

        with tempfile.TemporaryDirectory() as directory:
            with patch("scraper_hogarencuba.fetch", side_effect=fake_fetch), patch("scraper_hogarencuba.time.sleep"):
                frame = run(max_pages=1, delay=0, output_dir=Path(directory))
            self.assertEqual(frame["paginas_total_detectadas"].iloc[0], 2)
            self.assertEqual(frame["paginas_procesadas"].iloc[0], 1)
            self.assertFalse(frame["recoleccion_completa"].iloc[0])

    def test_hogarencuba_revalidation_preserves_source_and_updates_only_discrepancies(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            output = Path(directory) / "revalidated.csv"
            pd.DataFrame([
                {
                    "id_local": "HEC123",
                    "url": "https://hogarencuba.com/la-habana/HEC123-casa",
                    "titulo": "HEC123 Casa sin precio",
                    "precio_original": "40000",
                    "moneda": "USD",
                    "texto_evidencia": "Sin precio",
                },
                {
                    "id_local": "HEC124",
                    "url": "https://hogarencuba.com/la-habana/HEC124-casa",
                    "titulo": "HEC124 Casa por $ 10.000",
                    "precio_original": "10000",
                    "moneda": "USD",
                    "texto_evidencia": "Casa por $ 10.000",
                },
            ]).to_csv(source, index=False, encoding="utf-8-sig")

            def fake_fetch(url):
                return '''
                <script type="application/ld+json">
                {"@type":"Product","sku":"HEC123","offers":{"price":42000,"priceCurrency":"USD"}}
                </script>
                '''

            rows, updated = revalidar(source, output, delay=0, fetcher=fake_fetch)
            result = pd.read_csv(output, dtype=str, encoding="utf-8-sig")
            original = pd.read_csv(source, dtype=str, encoding="utf-8-sig")
            self.assertEqual((rows, updated), (2, 1))
            self.assertEqual(result.loc[0, "precio_original"], "42000.0")
            self.assertEqual(result.loc[0, "precio_previo_revalidacion"], "40000")
            self.assertEqual(result.loc[0, "revalidacion_estado"], "revalidado_live")
            self.assertEqual(result.loc[1, "revalidacion_estado"], "sin_discrepancia_en_evidencia_local")
            self.assertEqual(original.loc[0, "precio_original"], "40000")
            with self.assertRaises(FileExistsError):
                revalidar(source, output, delay=0, fetcher=fake_fetch)

    def test_hogarencuba_revalidation_selects_newest_largest_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            small = folder / "viviendas_hogarencuba_20261017_230809.csv"
            old = folder / "viviendas_hogarencuba_revisada_20261017_014824.csv"
            new = folder / "viviendas_hogarencuba_revalidada_20261017_232654.csv"
            pd.DataFrame({"id_local": ["HEC1"]}).to_csv(small, index=False)
            pd.DataFrame({"id_local": ["HEC1", "HEC2"]}).to_csv(old, index=False)
            pd.DataFrame({"id_local": ["HEC1", "HEC2"]}).to_csv(new, index=False)
            os.utime(old, (100, 100))
            os.utime(new, (200, 200))
            self.assertEqual(latest_source(folder), new)

    def test_hogarencuba_rejects_invalid_run_limits(self):
        with self.assertRaisesRegex(ValueError, "al menos 1"):
            run(max_pages=0)
        with self.assertRaisesRegex(ValueError, "no puede ser negativo"):
            run(max_pages=1, delay=-1)
        with self.assertRaisesRegex(ValueError, "entre 1 y 5"):
            run(max_pages=1, workers=6)

    def test_reprocessing_preserves_source_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.csv"
            output = Path(directory) / "reprocessed.csv"
            original_text = "Precio 49.000,00 €"
            with source.open("w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.DictWriter(handle, fieldnames=[
                    "precio", "moneda", "moneda_original", "texto_tarjeta", "url"
                ])
                writer.writeheader()
                writer.writerow({
                    "precio": "49000.0",
                    "moneda": "EUR",
                    "moneda_original": "EUR",
                    "texto_tarjeta": original_text,
                    "url": "https://example.test/casa-49000-cuc.htm",
                })
            self.assertEqual(reprocesar(source, output), 1)
            with output.open("r", newline="", encoding="utf-8-sig") as handle:
                result = next(csv.DictReader(handle))
            self.assertEqual(result["moneda"], "CUC")
            self.assertEqual(result["precio"], "49000.0")
            self.assertEqual(result["moneda_previa_reprocesamiento"], "EUR")
            self.assertEqual(result["texto_tarjeta"], original_text)
            with self.assertRaises(FileExistsError):
                reprocesar(source, output)
            with source.open("r", newline="", encoding="utf-8-sig") as handle:
                self.assertEqual(next(csv.DictReader(handle))["moneda"], "EUR")


class CurrencyConversionAndAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rates = pd.DataFrame([{
            "usd_informal_cup": "800",
            "eur_informal_cup": "900",
            "usd_formal_cup": "400",
            "eur_formal_cup": "500",
        }])

    def test_integration_prefers_newest_hogar_snapshot_when_row_counts_tie(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "outputs" / "hogarencuba"
            folder.mkdir(parents=True)
            old = folder / "viviendas_hogarencuba_revisada_20261017_014824.csv"
            new = folder / "viviendas_hogarencuba_revalidada_20261017_232654.csv"
            pd.DataFrame({"id_local": ["HEC1", "HEC2"]}).to_csv(old, index=False)
            pd.DataFrame({"id_local": ["HEC1", "HEC2"]}).to_csv(new, index=False)
            os.utime(old, (100, 100))
            os.utime(new, (200, 200))
            self.assertEqual(hogarencuba_source_path(Path(directory)), new)

    def test_cuc_remains_unconverted_without_cuc_rate(self):
        frame = pd.DataFrame([
            {"precio_original": 100, "moneda": "CUC", "precio_sospechoso": False},
            {"precio_original": 100, "moneda": "USD", "precio_sospechoso": False},
            {"precio_original": 100, "moneda": None, "precio_sospechoso": False},
            {"precio_original": 100, "moneda": "SIN_MONEDA", "precio_sospechoso": False},
        ])
        converted = convertir(frame, self.rates)
        self.assertTrue(pd.isna(converted.loc[0, "precio_usd_informal"]))
        self.assertEqual(converted.loc[0, "conversion_estado_informal"], "tasa_cuc_no_disponible")
        self.assertEqual(converted.loc[1, "precio_usd_informal"], 100)
        self.assertEqual(converted.loc[2, "conversion_estado_informal"], "moneda_no_identificada")
        self.assertEqual(converted.loc[3, "conversion_estado_informal"], "moneda_no_identificada")

    def test_cuc_uses_only_explicit_registered_rates(self):
        frame = pd.DataFrame([{
            "precio_original": 100,
            "moneda": "CUC",
            "precio_sospechoso": False,
        }])
        rates = self.rates.assign(cuc_informal_cup="1000", cuc_formal_cup="500")
        converted = convertir(frame, rates)
        self.assertEqual(converted.loc[0, "precio_usd_informal"], 125)
        self.assertEqual(converted.loc[0, "precio_usd_formal"], 125)

    def test_cuc_nominal_conversion_is_opt_in_and_keeps_suspicious_prices_unconverted(self):
        frame = pd.DataFrame([
            {"precio_original": 100, "moneda": "CUC", "precio_sospechoso": False, "fecha_publicacion": "17/10/2023"},
            {"precio_original": 1, "moneda": "CUC", "precio_sospechoso": True, "fecha_publicacion": "17/10/2023"},
            {"precio_original": 100, "moneda": "USD", "precio_sospechoso": False, "fecha_publicacion": "17/10/2023"},
        ])
        converted = convertir(frame, self.rates, cuc_usd_nominal=True)
        self.assertEqual(converted.loc[0, "precio_usd_informal"], 100)
        self.assertEqual(converted.loc[0, "precio_usd_formal"], 100)
        self.assertEqual(converted.loc[0, "conversion_estado_informal"], "convertido_nominal_1_CUC_1_USD")
        self.assertTrue(pd.isna(converted.loc[1, "precio_usd_informal"]))
        self.assertEqual(converted.loc[1, "conversion_estado_informal"], "precio_sospechoso")
        self.assertEqual(converted.loc[2, "precio_usd_informal"], 100)
        self.assertEqual(
            converted.loc[0, "metodo_conversion_cuc"],
            "nominal_1_CUC_igual_1_USD_anuncio_post_2021_confirmado_por_usuario_2026-10-18",
        )
        self.assertEqual(converted.loc[0, "fx_cuc_usd_nominal"], 1.0)
        self.assertTrue(pd.isna(converted.loc[0, "fx_cuc_informal_cup"]))

    def test_conversion_usa_precio_reextraido_cuando_el_campo_es_sospechoso(self):
        frame = pd.DataFrame([
            {
                "precio_original": 18,
                "moneda": "CUC",
                "precio_sospechoso": True,
                "precio_reextraido": 18000,
                "moneda_reextraida": "USD",
                "fecha_publicacion": "2026-05-01",
            },
            {
                "precio_original": 10,
                "moneda": "USD",
                "precio_sospechoso": True,
                "precio_reextraido": np.nan,
                "moneda_reextraida": "",
                "fecha_publicacion": "2026-05-01",
            },
        ])
        converted = convertir(frame, self.rates)
        # Reextraccion verificada: se analiza el precio de la descripcion, no el campo.
        self.assertEqual(converted.loc[0, "precio_analisis"], 18000)
        self.assertEqual(converted.loc[0, "moneda_analisis"], "USD")
        self.assertEqual(converted.loc[0, "precio_usd_informal"], 18000)
        self.assertEqual(converted.loc[0, "conversion_estado_informal"], "convertido")
        # Sospechoso sin reextraccion sigue excluido.
        self.assertTrue(pd.isna(converted.loc[1, "precio_usd_informal"]))
        self.assertEqual(converted.loc[1, "conversion_estado_informal"], "precio_sospechoso")

    def test_cuc_nominal_requires_post_2021_publication_date(self):
        frame = pd.DataFrame([
            {"precio_original": 100, "moneda": "CUC", "precio_sospechoso": False, "fecha_publicacion": "7/12/2019"},
            {"precio_original": 100, "moneda": "CUC", "precio_sospechoso": False, "fecha_publicacion": None},
            {"precio_original": 100, "moneda": "CUC", "precio_sospechoso": False, "fecha_publicacion": "Actualizado: hace 2 años"},
            {"precio_original": 100, "moneda": "CUC", "precio_sospechoso": False, "fecha_publicacion": "2023-10-17"},
        ])
        converted = convertir(frame, self.rates, cuc_usd_nominal=True)
        self.assertEqual(converted.loc[0, "conversion_estado_informal"], "cuc_pre_2021_no_convertido")
        self.assertTrue(pd.isna(converted.loc[0, "precio_usd_informal"]))
        self.assertEqual(converted.loc[1, "conversion_estado_informal"], "sin_fecha_no_confirma_post_2021")
        self.assertEqual(converted.loc[2, "conversion_estado_informal"], "sin_fecha_no_confirma_post_2021")
        self.assertEqual(converted.loc[3, "precio_usd_informal"], 100)
        self.assertEqual(converted.loc[3, "fx_cuc_usd_nominal"], 1.0)
        without_flag = convertir(frame, self.rates)
        self.assertTrue(without_flag["precio_usd_informal"].isna().all())
        self.assertTrue(
            without_flag["conversion_estado_informal"].eq("tasa_cuc_no_disponible").all()
        )

    def test_rate_selection_ignores_blocked_snapshots_without_rates(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            util = folder / "tasas_cambio_20261015_200919.csv"
            bloqueado = folder / "tasas_cambio_20261018_000000.csv"
            vacio = folder / "tasas_cambio_20261019_000000.csv"
            pd.DataFrame([{"fecha_utc": "2026-10-15", "usd_informal_cup": "796"}]).to_csv(util, index=False)
            pd.DataFrame([{"fecha_utc": "2026-10-18", "usd_informal_cup": None}]).to_csv(bloqueado, index=False)
            vacio.write_bytes(b"")
            self.assertEqual(latest_rate_file(folder, "tasas_cambio_*.csv"), util)
            pd.DataFrame([{"fecha_utc": "2026-10-20", "usd_informal_cup": None}]).to_csv(util, index=False)
            with self.assertRaises(ValueError):
                latest_rate_file(folder, "tasas_cambio_*.csv")

    def test_kmeans_returns_stable_groups_for_separated_blobs(self):
        data = np.array(
            [
                [0.0, 0.0], [0.0, 1.0], [1.0, 0.0],
                [10.0, 10.0], [10.0, 11.0], [11.0, 10.0],
                [20.0, 20.0], [20.0, 21.0], [21.0, 20.0],
            ]
        )
        labels, centroids = kmeans(data, k=3, seed=42)
        self.assertEqual(len(labels), len(data))
        self.assertEqual(len(np.unique(labels)), 3)
        self.assertEqual(centroids.shape, (3, 2))
        labels_repeat, _ = kmeans(data, k=3, seed=42)
        self.assertTrue((labels == labels_repeat).all())
        with self.assertRaises(ValueError):
            kmeans(data[:2], k=3)

    def test_aplica_veredictos_de_revision_manual_de_precios_bajos(self):
        frame = pd.DataFrame(
            [
                {"url": "https://ejemplo/a", "precio_sospechoso": False},
                {"url": "https://ejemplo/b", "precio_sospechoso": False},
                {"url": "https://ejemplo/c", "precio_sospechoso": False},
            ]
        )
        with tempfile.TemporaryDirectory() as folder:
            ruta = Path(folder) / "precios_bajos.csv"
            pd.DataFrame(
                [
                    {"url": "https://ejemplo/a", "veredicto": "Error"},
                    {"url": "https://ejemplo/b", "veredicto": "producto"},
                    {"url": "https://ejemplo/c", "veredicto": "venta"},
                ]
            ).to_csv(ruta, index=False)
            resultado = aplicar_veredictos_revision(frame, ruta)
        self.assertTrue(bool(resultado.loc[0, "precio_sospechoso"]))
        self.assertEqual(resultado.loc[0, "veredicto_revision"], "error")
        self.assertTrue(bool(resultado.loc[1, "precio_sospechoso"]))
        self.assertEqual(resultado.loc[1, "veredicto_revision"], "producto")
        # El veredicto "venta" queda registrado como revision, pero no excluye
        # el precio ni marca el anuncio como sospechoso.
        self.assertFalse(bool(resultado.loc[2, "precio_sospechoso"]))
        self.assertEqual(resultado.loc[2, "veredicto_revision"], "venta")

    def test_veredictos_vacios_no_modifican_el_maestro(self):
        frame = pd.DataFrame([{"url": "https://ejemplo/a", "precio_sospechoso": False}])
        with tempfile.TemporaryDirectory() as folder:
            ruta = Path(folder) / "no_existe.csv"
            resultado = aplicar_veredictos_revision(frame, ruta)
        self.assertFalse(bool(resultado.loc[0, "precio_sospechoso"]))
        self.assertIn("veredicto_revision", resultado.columns)

    def test_reextraccion_manual_registra_precio_verificado_y_evidencia(self):
        frame = pd.DataFrame(
            [
                {"url": "https://ejemplo/a", "precio_sospechoso": False},
                {"url": "https://ejemplo/b", "precio_sospechoso": False},
            ]
        )
        with tempfile.TemporaryDirectory() as folder:
            ruta = Path(folder) / "precios_bajos.csv"
            pd.DataFrame(
                [
                    {
                        "url": "https://ejemplo/a",
                        "veredicto": "Error",
                        "precio_en_descripcion": "18000",
                        "moneda_en_descripcion": "USD",
                        "observacion": "Descripcion cita 18 000 usd",
                    },
                    {
                        "url": "https://ejemplo/b",
                        "veredicto": "Error",
                        "precio_en_descripcion": "",
                        "moneda_en_descripcion": "",
                        "observacion": "Sin precio verificable",
                    },
                ]
            ).to_csv(ruta, index=False)
            resultado = aplicar_veredictos_revision(frame, ruta)
        # El campo publicado sigue marcado como erroneo; el precio verificado se
        # registra en columnas aparte con su evidencia.
        self.assertTrue(bool(resultado.loc[0, "precio_sospechoso"]))
        self.assertEqual(float(resultado.loc[0, "precio_reextraido"]), 18000.0)
        self.assertEqual(resultado.loc[0, "moneda_reextraida"], "USD")
        self.assertIn("18 000 usd", resultado.loc[0, "evidencia_precio"])
        # Sin precio verificado no hay reextraccion.
        self.assertTrue(pd.isna(resultado.loc[1, "precio_reextraido"]))
        self.assertEqual(str(resultado.loc[1, "moneda_reextraida"]).strip(), "")
        precio, moneda = precios_analisis(resultado)
        self.assertEqual(float(precio.loc[0]), 18000.0)
        self.assertEqual(moneda.loc[0], "USD")
        self.assertTrue(pd.isna(precio.loc[1]))

    def test_listas_adicionales_aportan_precio_sin_pisar_veredicto_manual(self):
        frame = pd.DataFrame(
            [
                {"url": "https://ejemplo/a", "precio_sospechoso": False},
                {"url": "https://ejemplo/b", "precio_sospechoso": False},
            ]
        )
        with tempfile.TemporaryDirectory() as folder:
            manual = Path(folder) / "precios_bajos.csv"
            ausentes = Path(folder) / "precios_ausentes.csv"
            pd.DataFrame(
                [
                    {"url": "https://ejemplo/a", "veredicto": "no_verificable",
                     "precio_en_descripcion": "", "moneda_en_descripcion": "",
                     "observacion": "revision manual: sin precio"},
                ]
            ).to_csv(manual, index=False)
            pd.DataFrame(
                [
                    {"url": "https://ejemplo/a", "veredicto": "precio_recuperado",
                     "precio_en_descripcion": "45000", "moneda_en_descripcion": "USD",
                     "observacion": "descripcion: 'Precio: 45.000 USD'"},
                    {"url": "https://ejemplo/b", "veredicto": "sin_precio_en_fuente",
                     "precio_en_descripcion": "", "moneda_en_descripcion": "",
                     "observacion": "pagina: Sin precio"},
                ]
            ).to_csv(ausentes, index=False)
            resultado = aplicar_veredictos_revision(frame, manual, adicionales=[ausentes])
        # La lista posterior aporta el precio recuperado como reextraccion...
        self.assertEqual(float(resultado.loc[0, "precio_reextraido"]), 45000.0)
        self.assertEqual(resultado.loc[0, "moneda_reextraida"], "USD")
        # ...pero el veredicto de la revision manual original se conserva.
        self.assertEqual(resultado.loc[0, "veredicto_revision"], "no_verificable")
        self.assertTrue(bool(resultado.loc[0, "precio_sospechoso"]))
        # El veredicto de la lista adicional tambien queda registrado y no excluye.
        self.assertEqual(resultado.loc[1, "veredicto_revision"], "sin_precio_en_fuente")
        self.assertFalse(bool(resultado.loc[1, "precio_sospechoso"]))
        precio, moneda = precios_analisis(resultado)
        self.assertEqual(float(precio.loc[0]), 45000.0)
        self.assertEqual(moneda.loc[0], "USD")

    def test_precios_analisis_prefiere_reextraccion_y_excluye_sospechosos(self):
        frame = pd.DataFrame(
            [
                {"precio_original": 18.0, "moneda": "CUC", "precio_sospechoso": True,
                 "precio_reextraido": 18000.0, "moneda_reextraida": "USD"},
                {"precio_original": 55000.0, "moneda": "USD", "precio_sospechoso": False,
                 "precio_reextraido": np.nan, "moneda_reextraida": ""},
                {"precio_original": 10.0, "moneda": "USD", "precio_sospechoso": True,
                 "precio_reextraido": np.nan, "moneda_reextraida": ""},
                {"precio_original": 20000.0, "moneda": "", "precio_sospechoso": False,
                 "precio_reextraido": np.nan, "moneda_reextraida": ""},
            ]
        )
        precio, moneda = precios_analisis(frame)
        # Reextraccion verificada gana sobre el campo erroneo.
        self.assertEqual(float(precio.loc[0]), 18000.0)
        self.assertEqual(moneda.loc[0], "USD")
        # Campo publicado usable.
        self.assertEqual(float(precio.loc[1]), 55000.0)
        self.assertEqual(moneda.loc[1], "USD")
        # Sospechoso sin reextraccion y campo sin moneda no aportan precio de analisis.
        self.assertTrue(pd.isna(precio.loc[2]))
        self.assertEqual(moneda.loc[2], "")
        self.assertTrue(pd.isna(precio.loc[3]))

    def test_precios_analisis_funciona_con_maestros_sin_columnas_de_reextraccion(self):
        frame = pd.DataFrame(
            [
                {"precio_original": 120.0, "moneda": "USD", "precio_sospechoso": False},
                {"precio_original": 5.0, "moneda": "USD", "precio_sospechoso": True},
            ]
        )
        precio, moneda = precios_analisis(frame)
        self.assertEqual(float(precio.loc[0]), 120.0)
        self.assertEqual(moneda.loc[0], "USD")
        self.assertTrue(pd.isna(precio.loc[1]))
        self.assertEqual(moneda.loc[1], "")

    def test_segments_are_calculated_separately_by_currency(self):
        frame = pd.DataFrame([
            {"precio_original": price, "habitaciones": 2, "banos": 1, "moneda": currency, "precio_sospechoso": False}
            for currency, prices in {"USD": [100, 200, 300], "EUR": [1000, 2000, 3000], "SIN_MONEDA": [1]}.items()
            for price in prices
        ])
        result = build_segments(frame)
        self.assertEqual(len(result), 6)
        self.assertEqual(result.groupby("moneda")["grupo_precio"].first().to_dict(), {
            "EUR": "economica",
            "USD": "economica",
        })
        self.assertEqual(result.groupby(["moneda", "grupo_precio"]).size().groupby("moneda").sum().to_dict(), {
            "EUR": 3,
            "USD": 3,
        })

    def test_channel_price_summary_keeps_currency_separate_and_excludes_small_groups(self):
        frame = pd.DataFrame(
            [
                {"fuente": "Cubisima", "canal": "plataforma", "precio_original": 100 + index, "moneda": "USD", "habitaciones": 2, "banos": 1, "fecha_publicacion": None, "ubicacion_raw": None, "superficie_m2": None}
                for index in range(10)
            ]
            + [
                {"fuente": "Cubisima", "canal": "plataforma", "precio_original": 1000, "moneda": "EUR", "habitaciones": 2, "banos": 1, "fecha_publicacion": None, "ubicacion_raw": None, "superficie_m2": None},
                {"fuente": "Cubisima", "canal": "plataforma", "precio_original": 10, "moneda": "SIN_MONEDA", "habitaciones": 2, "banos": 1, "fecha_publicacion": None, "ubicacion_raw": None, "superficie_m2": None},
            ]
        )
        prepared = prepare(frame)
        summary = channel_summary(prepared)
        self.assertEqual(set(summary["moneda"]), {"USD"})
        self.assertEqual(dict(zip(summary["moneda"], summary["mediana_precio"])), {"USD": 104.5})
        self.assertEqual(summary_table(prepared).loc[0, "moneda_pct"], 91.7)

    def test_control_summary_excludes_currencies_and_source_pairs_below_threshold(self):
        frame = pd.DataFrame(
            [
                {"fuente": "A", "moneda_analisis": "USD", "precio_analisis": value}
                for value in range(10)
            ]
            + [
                {"fuente": "B", "moneda_analisis": "USD", "precio_analisis": value}
                for value in range(2)
            ]
            + [
                {"fuente": "A", "moneda_analisis": "CUC", "precio_analisis": value}
                for value in range(9)
            ]
            + [
                {"fuente": "A", "moneda_analisis": "EUR", "precio_analisis": value}
                for value in range(4)
            ]
        )
        filtered, excluded = prepare_summary_groups(frame)
        self.assertEqual(set(zip(filtered["fuente"], filtered["moneda_analisis"])), {("A", "USD")})
        self.assertEqual(len(filtered), 10)
        self.assertEqual(excluded, {
            "monedas_n_menor_5": 4,
            "pares_fuente_moneda_n_menor_10": 11,
        })

    def test_dated_output_helper_does_not_reuse_existing_path(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            first = nueva_ruta_salida(output_dir, "plot.png", "20261021_120000")
            self.assertEqual(first.name, "plot_20261021_120000.png")
            first.touch()
            second = nueva_ruta_salida(output_dir, "plot.png", "20261021_120000")
            self.assertEqual(second.name, "plot_20261021_120000_02.png")

    def test_municipality_filter_keeps_groups_with_five_or_more(self):
        frame = pd.DataFrame(
            [
                {"municipio_homologado": "Playa", "fuente": "Revolico"}
                for _ in range(5)
            ]
            + [
                {"municipio_homologado": "Cerro", "fuente": "Revolico"}
                for _ in range(4)
            ]
        )
        filtered, excluded = filtrar_municipios_por_fuente(frame)
        self.assertEqual(filtered["municipio_homologado"].unique().tolist(), ["Playa"])
        self.assertEqual(excluded.to_dict(), {("Cerro", "Revolico"): 4})

    def test_segment_summary_excludes_small_source_currency_and_profile_groups(self):
        frame = pd.DataFrame(
            [
                {
                    "fuente": "A",
                    "moneda_analisis": "USD",
                    "grupo_precio": "economica",
                    "perfil_habitaciones": "pequena",
                    "precio_analisis": 100,
                    "habitaciones": 1,
                    "banos": 1,
                }
                for _ in range(4)
            ]
            + [
                {
                    "fuente": "A",
                    "moneda_analisis": "USD",
                    "grupo_precio": "alta",
                    "perfil_habitaciones": "amplia",
                    "precio_analisis": 1000,
                    "habitaciones": 5,
                    "banos": 2,
                }
                for _ in range(6)
            ]
            + [
                {
                    "fuente": "B",
                    "moneda_analisis": "USD",
                    "grupo_precio": "alta",
                    "perfil_habitaciones": "amplia",
                    "precio_analisis": 1000,
                    "habitaciones": 5,
                    "banos": 2,
                }
                for _ in range(4)
            ]
        )
        summary = segment_summary_table(frame)
        self.assertEqual(summary["grupo_precio"].tolist(), ["alta"])
        self.assertEqual(summary["anuncios"].tolist(), [6])

    def test_visualization_normalizes_unknown_currency(self):
        frame = pd.DataFrame({
            "precio_original": [50, 100],
            "moneda": ["SIN_MONEDA", " usd "],
        })
        result = money_labels(frame)
        self.assertEqual(result["moneda"].tolist(), ["", "USD"])

    def test_rank_associations_are_separated_by_currency_and_require_ten_rows(self):
        frame = pd.DataFrame([
            {"fuente": source, "moneda": currency, "precio_original": price, "habitaciones": rooms,
             "banos": None, "superficie_m2": None}
            for source, currency, scale in [
                ("Cubisima", "CUC", 1),
                ("Revolico", "USD", 100),
            ]
            for price, rooms in [(100, 1), (200, 2), (300, 3), (400, 4), (500, 5),
                                 (600, 6), (700, 7), (800, 8), (900, 9), (1000, 10)]
            for price in [price * scale]
        ])
        result = rank_associations(frame)
        self.assertEqual(set(zip(result["fuente"], result["moneda"])), {
            ("Cubisima", "CUC"),
            ("Revolico", "USD"),
        })
        self.assertTrue(result["spearman_rho"].eq(1.0).all())


class MetadatosRevolicoTests(unittest.TestCase):
    """Metadatos de la pagina individual de anuncio: municipio, fecha y estado."""

    def html_anuncio(self, estado="PUBLISHED", municipio="MunicipalityType:46", fecha="2026-10-06T15:09:36.500Z", descripcion="Apto en Nuevo Vedado"):
        apollo = {
            "AdType:57183888": {
                "title": "Se renta apto 3 hab",
                "description": descripcion,
                "price": 300,
                "currency": "USD",
                "status": estado,
                "updatedOnByUser": fecha,
                "isSold": False,
                "municipality": {"__ref": municipio} if municipio else None,
                "province": {"__ref": "ProvinceType:1"},
            },
            "MunicipalityType:46": {"name": "Plaza"},
            "ProvinceType:1": {"name": "La Habana"},
        }
        import json
        datos = {"props": {"pageProps": {"__APOLLO_STATE__": apollo}}}
        return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(datos)}</script>'

    def test_parsea_municipio_fecha_y_descripcion_desde_apollo(self):
        resultado = parsear_pagina_anuncio(self.html_anuncio())
        self.assertEqual(resultado["estado"], "publicado")
        self.assertEqual(resultado["municipio"], "Plaza")
        self.assertEqual(resultado["metodo_municipio"], "apollo")
        self.assertEqual(resultado["provincia"], "La Habana")
        self.assertEqual(resultado["fecha_updated_on"], "2026-10-06T15:09:36.500Z")
        self.assertEqual(resultado["descripcion"], "Apto en Nuevo Vedado")
        self.assertEqual(resultado["precio_pagina"], "300 USD")
        self.assertFalse(bool(resultado["vendido"]))

    def test_anuncio_despublicado_e_inexistente_quedan_registrados(self):
        self.assertEqual(parsear_pagina_anuncio("<html>Anuncio despublicado</html>")["estado"], "despublicado")
        datos = '{"props":{"pageProps":{"errorCode":"AD_NOT_FOUND"}}}'
        self.assertEqual(
            parsear_pagina_anuncio(f'<script id="__NEXT_DATA__">{datos}</script>')["estado"],
            "anuncio_inexistente_AD_NOT_FOUND",
        )

    def test_sin_municipio_estructural_se_busca_en_el_texto(self):
        html = self.html_anuncio(municipio=None, descripcion="Vendo casa en Marianao, buena ubicacion")
        resultado = parsear_pagina_anuncio(html)
        self.assertEqual(resultado["municipio"], "Marianao")
        self.assertEqual(resultado["metodo_municipio"], "texto_titulo_o_descripcion")

    def test_texto_ambiguo_no_adivina_el_municipio(self):
        # Varias coincidencias en el texto no se resuelven a ciegas.
        self.assertEqual(buscar_municipio_en_texto("Casa en Marianao cerca de Playa"), "")

    def test_parsear_fecha_exacta_y_relativa(self):
        self.assertEqual(parsear_fecha_exacta("2026-09-19T17:30:20.821Z"), "2026-09-19")
        self.assertEqual(parsear_fecha_exacta("17/10/2023"), "2023-10-17")
        self.assertIsNone(parsear_fecha_exacta("Actualizado: hace 2 anos"))
        self.assertIsNone(parsear_fecha_exacta(""))

    def test_aplicar_metadatos_anade_municipio_y_fecha_sin_tocar_lo_publicado(self):
        frame = pd.DataFrame(
            [
                {"url": "https://revolico.com/item/a", "ubicacion_raw": ""},
                {"url": "https://revolico.com/item/b", "ubicacion_raw": "Nuevo Vedado"},
                {"url": "https://cubisima.com/item/c", "ubicacion_raw": "Playa"},
            ]
        )
        with tempfile.TemporaryDirectory() as folder:
            ruta = Path(folder) / "metadatos_revolico_20261018_000000.csv"
            pd.DataFrame(
                [
                    {"url": "https://revolico.com/item/a", "municipio": "Plaza", "metodo_municipio": "apollo",
                     "fecha_updated_on": "2026-10-06T15:09:36.500Z", "estado": "publicado", "vendido": "False"},
                    {"url": "https://revolico.com/item/b", "municipio": "", "metodo_municipio": "",
                     "fecha_updated_on": "", "estado": "http_403", "vendido": ""},
                ]
            ).to_csv(ruta, index=False)
            resultado = aplicar_metadatos_revolico(frame, ruta)
        # Municipio y fecha de la pagina del anuncio quedan en columnas aparte.
        self.assertEqual(resultado.loc[0, "municipio_reextraido"], "Plaza")
        self.assertEqual(resultado.loc[0, "fecha_reextraida"], "2026-10-06T15:09:36.500Z")
        self.assertEqual(resultado.loc[0, "estado_anuncio"], "publicado")
        # El campo publicado no se corrige; la url sin metadatos queda vacia.
        self.assertEqual(resultado.loc[1, "ubicacion_raw"], "Nuevo Vedado")
        self.assertEqual(resultado.loc[1, "municipio_reextraido"], "")
        self.assertEqual(resultado.loc[2, "municipio_reextraido"], "")

    def test_ubicacion_analisis_prefiere_el_municipio_de_la_pagina(self):
        from integrar_fuentes import ubicacion_analisis
        frame = pd.DataFrame(
            [
                {"ubicacion_raw": "", "municipio_reextraido": "Plaza"},
                {"ubicacion_raw": "Nuevo Vedado", "municipio_reextraido": "Plaza"},
                {"ubicacion_raw": "Nuevo Vedado", "municipio_reextraido": ""},
                {"ubicacion_raw": "", "municipio_reextraido": ""},
            ]
        )
        ubicacion, origen = ubicacion_analisis(frame)
        self.assertEqual(ubicacion.tolist(), ["Plaza", "Plaza", "Nuevo Vedado", ""])
        self.assertEqual(origen.tolist(), ["pagina_anuncio", "pagina_anuncio", "campo_publicado", "sin_dato"])


class DetalleAnunciosRevolicoTests(unittest.TestCase):
    """Extraccion de habitaciones y banos del texto de cada anuncio de Revolico."""

    def cantidad(self, texto, patrones):
        valor, _, _ = extraer_cantidad(texto, patrones)
        return valor

    def test_digitos_y_palabras_en_descripcion(self):
        self.assertEqual(self.cantidad("Apartamento con 3 cuartos y 2 banos", PATRONES_HABITACION), 3.0)
        self.assertEqual(self.cantidad("Apartamento con 3 cuartos y 2 banos", PATRONES_BANO), 2.0)
        self.assertEqual(self.cantidad("Un cuarto y un bano", PATRONES_HABITACION), 1.0)
        self.assertEqual(self.cantidad("Un cuarto y un bano", PATRONES_BANO), 1.0)
        self.assertEqual(self.cantidad("Dos dormitorios", PATRONES_HABITACION), 2.0)
        self.assertEqual(self.cantidad("4 hab", PATRONES_HABITACION), 4.0)

    def test_banos_con_fraccion(self):
        self.assertEqual(self.cantidad("2 banos y medio", PATRONES_BANO), 2.5)
        self.assertEqual(self.cantidad("Tiene medio bano social", PATRONES_BANO), 0.5)
        # El patron simple no debe duplicar el "2" del caso "y medio" como conflicto.
        valor, _, todos = extraer_cantidad("2 banos y medio", PATRONES_BANO)
        self.assertEqual(valor, 2.5)
        self.assertEqual(todos, [2.5])

    def test_notacion_habanera_y_slug(self):
        # "apto 2/4" son 2 dormitorios; el segundo numero es el total de cuartos.
        self.assertEqual(self.cantidad("Apto 2/4 en Nuevo Vedado", PATRONES_HABITACION), 2.0)
        slug = slug_desde_url("https://www.revolico.com/item/apto-3-cuartos-nuevo-vedado-12345678")
        self.assertEqual(slug, "apto 3 cuartos nuevo vedado")
        self.assertEqual(self.cantidad(slug, PATRONES_HABITACION), 3.0)

    def test_sin_mencion_no_se_imputa(self):
        self.assertIsNone(self.cantidad("Amplio y luminoso", PATRONES_HABITACION))
        self.assertIsNone(self.cantidad("", PATRONES_BANO))
        self.assertIsNone(self.cantidad("Tiene garaje", PATRONES_BANO))

    def test_conflicto_titulo_vs_descripcion_se_marca_sin_resolver(self):
        from types import SimpleNamespace
        fila = SimpleNamespace(
            titulo="Casa 3 cuartos",
            descripcion="Dispone de 5 cuartos y 2 banos",
            url="https://www.revolico.com/item/casa-12345678",
        )
        resultado = procesar(fila)
        # Gana la primera aparicion explicita (descripcion); el conflicto queda marcado.
        self.assertEqual(resultado["habitaciones_descripcion"], 5.0)
        self.assertEqual(resultado["habitaciones_titulo"], 3.0)
        self.assertIn("habitaciones titulo=3 descripcion=5", resultado["conflicto_detalle"])

    def test_aplicar_detalle_anuncios_prefiere_descripcion_y_documenta_borrados(self):
        frame = pd.DataFrame(
            [
                {"url": "https://revolico.com/item/a", "habitaciones": np.nan, "banos": np.nan},
                {"url": "https://revolico.com/item/b", "habitaciones": np.nan, "banos": np.nan},
                {"url": "https://revolico.com/item/c", "habitaciones": np.nan, "banos": np.nan},
                {"url": "https://revolico.com/item/d", "habitaciones": np.nan, "banos": np.nan},
            ]
        )
        with tempfile.TemporaryDirectory() as folder:
            ruta = Path(folder) / "detalle_anuncios_revolico_20261018_000000.csv"
            pd.DataFrame(
                [
                    {"url": "https://revolico.com/item/a", "estado": "publicado",
                     "habitaciones_descripcion": "3", "banos_descripcion": "2",
                     "habitaciones_slug": "", "banos_slug": "",
                     "evidencia_detalle": "habitaciones='3 cuartos'", "conflicto_detalle": "",
                     "fecha_snapshot_listado": "2026-09-29", "fecha_extraccion": "2026-10-18 12:00:00"},
                    {"url": "https://revolico.com/item/b",
                     "estado": "anuncio_inexistente_unpublished-ad",
                     "habitaciones_descripcion": "", "banos_descripcion": "",
                     "habitaciones_slug": "4", "banos_slug": "",
                     "evidencia_detalle": "", "conflicto_detalle": "",
                     "fecha_snapshot_listado": "2026-09-29", "fecha_extraccion": "2026-10-18 12:00:00"},
                    {"url": "https://revolico.com/item/d", "estado": "publicado",
                     "habitaciones_descripcion": "", "banos_descripcion": "",
                     "habitaciones_titulo": "1", "banos_titulo": "",
                     "habitaciones_slug": "", "banos_slug": "",
                     "evidencia_detalle": "habitaciones_titulo='1/4'", "conflicto_detalle": "",
                     "fecha_snapshot_listado": "2026-09-29", "fecha_extraccion": "2026-10-18 12:00:00"},
                ]
            ).to_csv(ruta, index=False)
            resultado = aplicar_detalle_anuncios(frame, ruta)
        # El anuncio publicado toma el valor de la descripcion.
        self.assertEqual(float(resultado.loc[0, "habitaciones_reextraido"]), 3.0)
        self.assertEqual(float(resultado.loc[0, "banos_reextraido"]), 2.0)
        self.assertEqual(resultado.loc[0, "evidencia_detalle"], "habitaciones='3 cuartos'")
        # El borrado conserva su slug y documenta la ventana de desaparicion.
        self.assertEqual(float(resultado.loc[1, "habitaciones_slug"]), 4.0)
        self.assertEqual(resultado.loc[1, "ventana_despublicacion"], "2026-09-29 a 2026-10-18")
        self.assertIn("aparecia en el listado guardado del 2026-09-29", resultado.loc[1, "justificacion_disponibilidad"])
        # El anuncio sin fila de detalle queda vacio, sin ventana ni imputacion.
        self.assertEqual(resultado.loc[2, "ventana_despublicacion"], "")
        self.assertTrue(pd.isna(resultado.loc[2, "habitaciones_reextraido"]))
        # Si la descripcion no menciona la cantidad, manda el titulo del anuncio
        # y la evidencia indica el campo de origen.
        self.assertEqual(float(resultado.loc[3, "habitaciones_reextraido"]), 1.0)
        self.assertEqual(resultado.loc[3, "evidencia_detalle"], "habitaciones_titulo='1/4'")
        self.assertEqual(resultado.loc[3, "ventana_despublicacion"], "")


class DetalleAnalisisTests(unittest.TestCase):
    """Regla de precedence: texto del anuncio, campo publicado, enlace (slug)."""

    def test_prefiere_descripcion_luego_publicado_luego_slug(self):
        frame = pd.DataFrame(
            [
                {"habitaciones_reextraido": 3.0, "habitaciones": np.nan, "habitaciones_slug": 5.0,
                 "banos_reextraido": 2.0, "banos": np.nan, "banos_slug": np.nan},
                {"habitaciones_reextraido": np.nan, "habitaciones": 2.0, "habitaciones_slug": 5.0,
                 "banos_reextraido": np.nan, "banos": 1.0, "banos_slug": np.nan},
                {"habitaciones_reextraido": np.nan, "habitaciones": np.nan, "habitaciones_slug": 4.0,
                 "banos_reextraido": np.nan, "banos": np.nan, "banos_slug": 1.0},
                {"habitaciones_reextraido": np.nan, "habitaciones": np.nan, "habitaciones_slug": np.nan,
                 "banos_reextraido": np.nan, "banos": np.nan, "banos_slug": np.nan},
            ]
        )
        hab, banos, origen_hab, origen_ban = detalle_analisis(frame)
        self.assertEqual(hab.tolist()[:3], [3.0, 2.0, 4.0])
        self.assertTrue(pd.isna(hab.tolist()[3]))
        self.assertEqual(banos.tolist()[:3], [2.0, 1.0, 1.0])
        self.assertTrue(pd.isna(banos.tolist()[3]))
        self.assertEqual(origen_hab.tolist(), ["descripcion_o_titulo", "campo_publicado", "slug", ""])
        self.assertEqual(origen_ban.tolist(), ["descripcion_o_titulo", "campo_publicado", "slug", ""])

    def test_sin_columnas_de_reextraccion_usa_el_campo_publicado(self):
        # Maestros antiguos y frames de prueba no traen columnas de reextraccion.
        frame = pd.DataFrame([{"habitaciones": 2.0, "banos": 1.0}])
        hab, banos, origen_hab, origen_ban = detalle_analisis(frame)
        self.assertEqual(float(hab.iloc[0]), 2.0)
        self.assertEqual(float(banos.iloc[0]), 1.0)
        self.assertEqual(origen_hab.iloc[0], "campo_publicado")
        self.assertEqual(origen_ban.iloc[0], "campo_publicado")


class ExclusionNoResidencialesTests(unittest.TestCase):
    """Los anuncios que no son vivienda en venta se apartan sin destruirlos."""

    def test_excluye_productos_permutas_y_conserva_las_viviendas(self):
        frame = pd.DataFrame(
            [
                {"url": "https://ejemplo/vivienda", "veredicto_revision": ""},
                {"url": "https://ejemplo/producto", "veredicto_revision": "producto"},
                {"url": "https://ejemplo/permuta", "veredicto_revision": "permuta"},
                {"url": "https://ejemplo/local", "veredicto_revision": "otro"},
                {"url": "https://ejemplo/borrado", "veredicto_revision": "despublicado"},
            ]
        )
        limpio, excluidos = excluir_no_residenciales(frame)
        self.assertEqual(len(limpio), 2)
        self.assertEqual(excluidos["veredicto_revision"].tolist(), ["producto", "permuta", "otro"])
        # Los borrados y el resto de anuncios permanecen en el dataset.
        self.assertIn("https://ejemplo/borrado", set(limpio["url"]))
        self.assertIn("https://ejemplo/vivienda", set(limpio["url"]))
        # Nada se destruye: los excluidos conservan todas sus columnas.
        self.assertEqual(len(excluidos.columns), len(frame.columns))

    def test_frames_sin_veredicto_no_pierden_filas(self):
        frame = pd.DataFrame([{"url": "https://ejemplo/a"}])
        limpio, excluidos = excluir_no_residenciales(frame)
        self.assertEqual(len(limpio), 1)
        self.assertTrue(excluidos.empty)


class TipoViviendaTests(unittest.TestCase):
    """El tipo de vivienda no se toma de la primera palabra del titulo."""

    def test_no_confunde_precio_o_telefono_con_tipo(self):
        self.assertEqual(clasificar_tipo_vivienda("30.000 USD Casa en el Vedado"), "casa")
        self.assertEqual(clasificar_tipo_vivienda("8.500 USD Apto 2/4 Centro Habana"), "apartamento")
        self.assertEqual(clasificar_tipo_vivienda("Vendo penthouse en Miramar"), "penthouse")
        self.assertEqual(clasificar_tipo_vivienda("Gestionamos la venta de tu vivienda"), "no_clasificado")
        self.assertIsNone(clasificar_tipo_vivienda(""))
        self.assertIsNone(clasificar_tipo_vivienda(None))
        self.assertTrue(pd.isna(clasificar_tipo_vivienda(np.nan)))


class PreciosAusentesTests(unittest.TestCase):
    """Recuperacion conservadora de precios en texto (revisar_precios_ausentes)."""

    def resolver_texto(self, texto, publicado=None):
        candidatos, rechazados = candidatos_de_texto(texto, "descripcion")
        return resolver(candidatos, rechazados, publicado)

    def test_recupera_un_unico_precio_explicito(self):
        veredicto, precio, moneda, _ = self.resolver_texto(
            "Se vende casa, precio: $ 5000 USD (Se acepta el pago aqui)"
        )
        self.assertEqual(veredicto, "precio_recuperado")
        self.assertEqual(precio, 5000.0)
        self.assertEqual(moneda, "USD")

    def test_dolares_solo_con_signo_no_basta_porque_puede_ser_cuc(self):
        veredicto, precio, _, _ = self.resolver_texto("Casa precio $ 45.000, se negocia")
        self.assertEqual(veredicto, "moneda_ambigua")
        self.assertIsNone(precio)

    def test_siete_digitos_sin_separador_se_toma_como_telefono(self):
        veredicto, precio, _, detalle = self.resolver_texto("Llamar al 4328353 usd o euros")
        self.assertEqual(veredicto, "solo_coincidencias_tipograficas")
        self.assertIsNone(precio)
        self.assertIn("telefono", detalle)

    def test_varios_importes_distintos_quedan_ambiguos(self):
        veredicto, precio, _, detalle = self.resolver_texto("Vendo en 45.000 USD o 50.000 USD")
        self.assertEqual(veredicto, "ambiguo")
        self.assertIsNone(precio)
        self.assertIn("45000 USD", detalle)
        self.assertIn("50000 USD", detalle)

    def test_no_aplica_valores_fuera_de_rango_ni_cup_sin_validar(self):
        veredicto, _, _, _ = self.resolver_texto("Casa por 1 USD")
        self.assertEqual(veredicto, "valor_improbable")
        veredicto, _, _, _ = self.resolver_texto("Apartamento 25.000 cup")
        self.assertEqual(veredicto, "cup_requiere_validacion")
        veredicto, _, _, _ = self.resolver_texto("Precio 80.000 mlc")
        self.assertEqual(veredicto, "moneda_sin_tasa")

    def test_no_repara_con_el_mismo_valor_sospechoso_del_campo_publicado(self):
        veredicto, precio, _, detalle = self.resolver_texto("Vendo casa en 10 USD", publicado=10.0)
        self.assertEqual(veredicto, "solo_coincide_con_publicado")
        self.assertIsNone(precio)
        self.assertIn("publicado", detalle)

    def test_precio_en_url_de_cubisima(self):
        candidatos, _ = candidatos_de_url(
            "https://www.cubisima.com/casas/casa-de-1-cuarto-10-cuc-en-calle-86!504281.htm"
        )
        self.assertEqual([(c["valor"], c["moneda"]) for c in candidatos], [(10.0, "CUC")])
        # Las URLs numericas de Revolico no contienen precio.
        candidatos, _ = candidatos_de_url("https://www.revolico.com/item/vendo-casa-56750346")
        self.assertEqual(candidatos, [])

    def test_politica_de_consulta_no_confunde_falla_con_ausencia(self):
        # Pagina consultada y viva (Revolico responde 'published'): si no cita
        # precio, la ausencia se afirma con evidencia.
        for estado in ("published", "publicado"):
            veredicto, _ = aplicar_politica_consulta(
                "sin_precio_en_texto", "x", True, estado, False
            )
            self.assertEqual(veredicto, "sin_precio_en_texto")
        # HTTP que no responde: jamas se afirma que el precio no existe.
        for estado in ("http_403", "error_http", "http_500"):
            veredicto, detalle = aplicar_politica_consulta(
                "sin_precio_en_texto", "x", True, estado, False
            )
            self.assertEqual(veredicto, "consulta_fallida")
            self.assertIn(estado, detalle)
        # Sin red, sin consulta y sin anuncio: los otros tres veredictos.
        self.assertEqual(
            aplicar_politica_consulta("sin_precio_en_texto", "x", True, "no_consultado_sin_red", False)[0],
            "no_consultado_sin_red",
        )
        self.assertEqual(
            aplicar_politica_consulta(
                "sin_precio_en_texto", "x", True, "anuncio_inexistente_cant-see-deleted-ad", False
            )[0],
            "anuncio_no_disponible",
        )
        self.assertEqual(
            aplicar_politica_consulta("sin_precio_en_texto", "x", False, "no_aplica", True)[0],
            "anuncio_no_disponible",
        )
        # Los veredictos distintos de "sin_precio_en_texto" no se tocan.
        self.assertEqual(
            aplicar_politica_consulta("ambiguo", "x", True, "http_403", False)[0], "ambiguo"
        )


class ProcesarEntrevistasTests(unittest.TestCase):
    """Anonimizacion, privacidad y codificacion de entrevistas."""

    @staticmethod
    def raw_frame():
        # La ultima pregunta del export real trae un espacio final que rompia el rename.
        canales = next(k for k, v in QUESTIONS.items() if v == "canales") + " "
        return pd.DataFrame([{
            "Marca temporal": "2026-10-15 21:32:57.907000",
            "Dirección de correo electrónico": "persona@example.com",
            "Cuál es su relación con la vivienda?": "Propietario",
            canales: "Grupos de Telegram y WhatsApp en Playa",
        }])

    def test_prepare_frame_anonima_y_renombra(self):
        frame = prepare_frame(self.raw_frame())
        self.assertEqual(frame.loc[0, "entrevista_id"], "E01")
        self.assertIn("canales", frame.columns)         # rename con espacio final
        self.assertNotIn("fecha_respuesta_mal", frame.columns)
        self.assertEqual(frame.loc[0, "fecha_respuesta"], "2026-10-15 21:32:57")
        # Privacidad: ninguna columna de metadatos personales sobrevive.
        self.assertFalse(any("correo" in c.casefold() for c in frame.columns))
        self.assertFalse(any("persona@example.com" in str(v) for v in frame.values.ravel()))

    def test_build_coded_secuencia_e(self):
        raw = pd.concat([self.raw_frame(), self.raw_frame()], ignore_index=True)
        coded = build_coded(prepare_frame(raw))
        self.assertEqual(list(coded["entrevista_id"]), ["E01", "E02"])
        for code in ("C1_necesidad_economica", "C2_migracion", "C3_moneda_tasa",
                     "C4_canal_venta", "C5_precio_alto", "C6_caracteristicas",
                     "C7_municipio", "A1_cita"):
            self.assertIn(code, coded.columns)
        # La respuesta de canales menciona Telegram/WhatsApp/Playa.
        self.assertEqual(int(coded.loc[0, "C4_canal_venta"]), 1)
        self.assertEqual(int(coded.loc[0, "C7_municipio"]), 1)

    def test_code_row_acento_insensible(self):
        row = pd.Series({
            "evolucion_precios": "La travesía por Nicaragua y la emigración",
            "factores_precio": "los banos y la piscina",
            "influencia_tasas": "todo se rige por la tasa de cambio",
            "municipio": "Diez de Octubre",
        })
        codes = code_row(row)
        self.assertEqual(codes["C2_migracion"], 1)   # "travesía" acentuada
        self.assertEqual(codes["C3_moneda_tasa"], 1)  # "tasa" en singular
        self.assertEqual(codes["C6_caracteristicas"], 1)  # "banos" sin tilde
        self.assertEqual(codes["C7_municipio"], 1)   # municipio fuera de la lista vieja

    def test_code_row_migracion_sin_palabra_migra(self):
        row = pd.Series({"influencia_migracion": "vender para poder salir del país"})
        self.assertEqual(code_row(row)["C2_migracion"], 1)

    def test_load_responses_formatos(self):
        with self.assertRaises(FileNotFoundError):
            load_responses(Path("no_existe_export.xlsx"))
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as handle:
            handle.write(b"x")
            ruta = Path(handle.name)
        try:
            with self.assertRaises(ValueError):
                load_responses(ruta)
        finally:
            os.unlink(ruta)


if __name__ == "__main__":
    unittest.main()
