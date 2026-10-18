import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from comparativo_fuentes import channel_summary, prepare, summary_table
from convertir_precios_tasas import convertir, latest_rate_file
from integrar_fuentes import hogarencuba_source_path
from analisis_preguntas import rank_associations
from precio_moneda import extraer_precio_moneda, normalizar_moneda, parsear_importe
from reprocesar_cubisima import reprocesar
from reprocesar_hogarencuba import latest_source, revalidar
from scraper_cubisima_online import (
    detectar_paginas,
    extraer_anuncios_pagina,
    extraer_datos_tarjeta,
    validar_respuesta,
)
from scraper_hogarencuba import detect_pages, list_links, parse_detail, run
from segmentacion_viviendas import build_segments
from visualizaciones_fuentes import money_labels


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

    def test_channel_price_summary_keeps_currency_separate(self):
        frame = pd.DataFrame([
            {"fuente": "Cubisima", "canal": "plataforma", "precio_original": 100, "moneda": "USD", "habitaciones": 2, "banos": 1, "fecha_publicacion": None, "ubicacion_raw": None, "superficie_m2": None},
            {"fuente": "Cubisima", "canal": "plataforma", "precio_original": 1000, "moneda": "EUR", "habitaciones": 2, "banos": 1, "fecha_publicacion": None, "ubicacion_raw": None, "superficie_m2": None},
            {"fuente": "Cubisima", "canal": "plataforma", "precio_original": 10, "moneda": "SIN_MONEDA", "habitaciones": 2, "banos": 1, "fecha_publicacion": None, "ubicacion_raw": None, "superficie_m2": None},
        ])
        prepared = prepare(frame)
        summary = channel_summary(prepared)
        self.assertEqual(set(summary["moneda"]), {"USD", "EUR"})
        self.assertEqual(dict(zip(summary["moneda"], summary["mediana_precio"])), {"EUR": 1000, "USD": 100})
        self.assertEqual(summary_table(prepared).loc[0, "moneda_pct"], 66.7)

    def test_visualization_normalizes_unknown_currency(self):
        frame = pd.DataFrame({
            "precio_original": [50, 100],
            "moneda": ["SIN_MONEDA", " usd "],
        })
        result = money_labels(frame)
        self.assertEqual(result["moneda"].tolist(), ["", "USD"])

    def test_rank_associations_are_separated_by_currency_and_require_five_rows(self):
        frame = pd.DataFrame([
            {"fuente": source, "moneda": currency, "precio_original": price, "habitaciones": rooms,
             "banos": None, "superficie_m2": None}
            for source, currency, scale in [
                ("Cubisima", "CUC", 1),
                ("Revolico", "USD", 100),
            ]
            for price, rooms in [(100, 1), (200, 2), (300, 3), (400, 4), (500, 5)]
            for price in [price * scale]
        ])
        result = rank_associations(frame)
        self.assertEqual(set(zip(result["fuente"], result["moneda"])), {
            ("Cubisima", "CUC"),
            ("Revolico", "USD"),
        })
        self.assertTrue(result["spearman_rho"].eq(1.0).all())


if __name__ == "__main__":
    unittest.main()
