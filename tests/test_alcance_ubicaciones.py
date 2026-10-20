"""Pruebas de alcance geografico y homologacion de municipios."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from integrar_fuentes import excluir_fuera_de_alcance
from ubicaciones import homologar_municipio


class UbicacionesTests(unittest.TestCase):
    def test_homologa_variantes_de_municipios_de_la_habana(self):
        self.assertEqual(homologar_municipio("Plaza"), "Plaza de la Revolución")
        self.assertEqual(homologar_municipio("Plaza De La Revolucion"), "Plaza de la Revolución")
        self.assertEqual(homologar_municipio("Diez De Octubre"), "Diez de Octubre")
        self.assertEqual(homologar_municipio("10 de Octubre"), "Diez de Octubre")
        self.assertEqual(homologar_municipio("La Habana Del Este"), "Habana del Este")
        self.assertEqual(homologar_municipio("Habana del Este"), "Habana del Este")
        self.assertEqual(homologar_municipio("San Miguel Del Padron"), "San Miguel del Padrón")
        self.assertEqual(homologar_municipio("La Lisa"), "La Lisa")

    def test_no_imputa_zonas_o_municipios_de_otras_provincias(self):
        for valor in ["Vedado", "Miramar", "Santa Clara", "San Cristóbal", "Colón", "", None]:
            self.assertEqual(homologar_municipio(valor), "")


class AlcanceTests(unittest.TestCase):
    def test_excluye_por_url_y_conserva_el_motivo(self):
        frame = pd.DataFrame([
            {"fuente": "Revolico", "url": "https://ejemplo.test/1", "titulo": "Casa en Playa"},
            {"fuente": "Revolico", "url": "https://ejemplo.test/2", "titulo": "Casa en Artemisa"},
            {"fuente": "Cubisima", "url": "https://ejemplo.test/3", "titulo": "Apartamento"},
        ])
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "exclusiones.csv"
            pd.DataFrame([
                {
                    "fuente": "Revolico",
                    "id_local": "rev_000002",
                    "url": "https://ejemplo.test/2",
                    "motivo": "fuera_de_la_habana",
                    "evidencia": "Titulo: casa en Artemisa",
                }
            ]).to_csv(ruta, index=False)
            filtrado, excluidos = excluir_fuera_de_alcance(frame, ruta)
        self.assertEqual(len(filtrado), 2)
        self.assertEqual(len(excluidos), 1)
        self.assertEqual(excluidos.iloc[0]["url"], "https://ejemplo.test/2")
        self.assertEqual(excluidos.iloc[0]["motivo_alcance"], "fuera_de_la_habana")
        self.assertIn("titulo", filtrado.columns)

    def test_sin_lista_no_excluye_nada(self):
        frame = pd.DataFrame([{"url": "https://ejemplo.test/1"}])
        filtrado, excluidos = excluir_fuera_de_alcance(frame, None)
        self.assertEqual(len(filtrado), 1)
        self.assertTrue(excluidos.empty)

    def test_lista_sin_columnas_requeridas_falla_claro(self):
        frame = pd.DataFrame([{"url": "https://ejemplo.test/1"}])
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "exclusiones.csv"
            pd.DataFrame([{"id_local": "x"}]).to_csv(ruta, index=False)
            with self.assertRaises(ValueError):
                excluir_fuera_de_alcance(frame, ruta)


if __name__ == "__main__":
    unittest.main()
