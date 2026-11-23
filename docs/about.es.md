# Acerca de

## wildintel-trapper-sdk y WildINTEL

**wildintel-trapper-sdk** es un cliente Python tipado para la API REST de
[Trapper](https://gitlab.com/trapper-project/trapper), la plataforma de código abierto para gestionar y
clasificar datos de fototrampeo: localizaciones, despliegues, recursos multimedia, colecciones de
almacenamiento, proyectos de investigación y resultados de clasificación, tanto manual como asistida
por IA.

Existe para ofrecer a las demás herramientas de la cadena de [WildINTEL](https://wildintel.eu/), como
[wildintel-publisher](https://github.com/wildintelproject/wildintel-publisher), que obtiene paquetes
Camtrap DP de un proyecto de clasificación de Trapper para publicarlos en repositorios de datos
abiertos, una forma única, tipada y bien probada de comunicarse con un servidor Trapper, en lugar de
que cada herramienta reimplemente sus propias llamadas HTTP y su gestión de paginación.

La biblioteca cubre por completo la API REST de Trapper, y añade acceso de escritura a los dos recursos
que la API no expone (localizaciones y despliegues) simulando los formularios de importación de la
interfaz web: una solución documentada, no un contrato estable de la API, y claramente separada del
resto de la interfaz del cliente. Funciona con Trapper v1 y v2.

---

## Financiación

Este trabajo forma parte del [proyecto WildINTEL](https://wildintel.eu/), financiado por la
convocatoria conjunta de investigación 2022–2023 de [Biodiversa+](https://www.biodiversa.eu/)
*"Improved transnational monitoring of biodiversity and ecosystem change for science and society
(BiodivMon)"*.

Biodiversa+ es la asociación europea cofinanciada para la biodiversidad que apoya investigación de
excelencia con impacto en las políticas y en la sociedad. Biodiversa+ forma parte de la Estrategia de
Biodiversidad de la UE para 2030, que busca poner la biodiversidad de Europa en una senda de
recuperación para 2030, y está cofinanciada por la Comisión Europea.

---

## Licencia

Este proyecto se distribuye bajo la [GNU General Public License v3.0 o posterior](https://www.gnu.org/licenses/gpl-3.0.html).
