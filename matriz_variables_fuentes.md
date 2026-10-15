# Matriz de variables por fuente

<|constrain|> Fuente | Rol actual | Precio | Moneda | Municipio/zona | Habitaciones | Banos | Superficie m2 | Fecha | Caracteristicas | Agencia | Acceso |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Revolico (`anuncios_revolico_procesados.csv`) | Fuente principal de anuncios informales | 734/780 | 734/780 | 289/780 | 70/780 | 0/780 | 20 titulos | no | texto contaminado; no confiable | desconocido | Scraping directo bloqueado; paginas guardadas viable |
| Cubisima local (`viviendas_cubisima.csv`) | Fuente complementaria rica en banos/zona | 571/625 | 571/625 | 625/625 | 555/625 | 625/625 | no observado | si | booleanos u estructurados | desconocido | Accumulado; precio presente en 571 |
| Cubisima online (`outputs/cubisima/...`) | Actualizacion estructural reciente | 0/598 en esta pasada | 0/598 | 598/598 | 555/598 | 598/598 | no observado | si | booleanos | desconocido | Accesible; parser no capturo precio en esta pasada |
| Casas Oasis (`casasoasis.cu`) | Candidata para datos estructurados | por verificar | USD/CUP | por verificar | probable | probable | probable | probable | mayor detalle | gerente particular/agencia | Accesible publicamente |
| HogarEnCuba (`hogarencuba.com`) | Candidata para un mercado mas filtrable | promedio declarado por municipio | USD | si filtros | si filtros | si | por verificar | por verificar | ficha, fotos, contacto | agentes/particulares | Accesible con carga filtrada |
| Busca Tu Choza (`buscatuschoza.cu`) | Candidata a clasificado local | por verificar | por verificar | por verificar | probable | probable | por verificar | por verificar | media | desconocido | Accesible por verificacion |

Interpretacion:
- Revolico es mas escaso en banos y municipio, pero es la fuente principal de precio.
- Cubisima es mas rica en estructura y zona; su refresco actual no reporto precio en todas las tarjetas, por eso se conserva un archivo Cubisima previo para conversion.
- Casas Oasis/HogarEnCuba podran aportar superficie real si se construye un extractor diferente.
- Antes de comparar canales formales e informales, hay que observar agente/visible en fichas; el dataset actual no trae ese campo.
