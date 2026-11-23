# Características

## Lectura de datos

- **Un componente por recurso:** cada endpoint de Trapper (localizaciones, despliegues, recursos,
  colecciones, proyectos de investigación, proyectos de clasificación, clasificaciones,
  clasificaciones de IA, ...) tiene su propia clase con una interfaz coherente.
- **Compatible con Trapper v1 y v2:** la versión del servidor se detecta automáticamente y los
  componentes que solo existen en una de ellas lo indican y lanzan `UnsupportedVersionError` en la
  otra. Consulta [Versiones de Trapper](guide/versions.md).
- **Seis patrones de acceso en cada componente:** `get()` para una página, `get_all()`/`all()` para
  unir todas las páginas en un único resultado, `where()` para paginación perezosa bajo demanda,
  `find(pk)` para un único elemento y `export()` para volcar los resultados directamente a un CSV.
  Consulta [Uso](usage.md).
- **Paginación transparente:** `where()` pide las páginas mientras iteras; `get_all()` recorre todas
  las páginas y une los resultados, así que nunca tienes que escribir a mano un bucle por número de
  página.
- **Filtrado mediante argumentos con nombre:** cada componente documenta sus propios campos de
  filtro (rangos de fechas, PK, búsqueda de texto libre, ...), que se pasan tal cual como parámetros
  de consulta.
- **Exportación a CSV:** los resultados de cualquier componente pueden escribirse directamente en un
  CSV con una sola llamada `export(file=...)`, o devolverse como una lista de modelos tipados cuando
  `file=None`.

---

## Modelos tipados

- **Pydantic v2 en cada respuesta:** autocompletado completo en el IDE, y los errores de validación
  aparecen de inmediato en lugar de fallar más tarde por un campo ausente o mal tipado.
- **Esquemas CamtrapDP y de Trapper:** los endpoints que pueden devolver cualquiera de los dos
  formatos (p. ej. las filas exportadas de clasificaciones o clasificaciones de IA) se modelan como
  una `Union` y se resuelven automáticamente según los campos presentes.
- **Validadores defensivos:** los campos opcionales que el servidor a veces envía como cadena vacía
  en lugar de omitirlos (fechas, números, booleanos) se normalizan a `None` en lugar de lanzar un
  `ValidationError`.

---

## Acceso de escritura donde la API REST se queda corta

- **Importación de clasificaciones: un endpoint REST real, con autenticación por token:**
  `client.classification_results.import_classifications()` envía un CSV a
  `media_classification/api/classifications/import/` para volver a aplicar datos de clasificación de
  expertos o de IA (especie, recuento, aprobación, ...) a observaciones existentes, emparejadas por su
  `_id` interno.
- **Importación de localizaciones y despliegues: una solución documentada:** la API REST es de solo
  lectura para estos dos recursos, así que `client.locations.import_locations()` y
  `client.deployments.import_deployments()` simulan los formularios de importación de la interfaz web
  (en Trapper v2, la acción de importación del admin de Django) con autenticación por cookie/sesión en
  lugar del token de la API. Esto **no** es un contrato estable de la API: consulta la guía de cada
  componente antes de depender de ello.
- **Subidas por fragmentos para CSV grandes:** los tres métodos de importación aceptan
  `split`/`delay`/`chunk_size` para dividir un CSV grande en varios fragmentos autocontenidos (cada
  uno repite la fila de cabecera), subidos de uno en uno con una pausa entre ellos. Es una solución
  para servidores que rechazan o agotan el tiempo con subidas de un único fichero muy grande.
- **Reintento automático ante fallos de red:** `retry_attempts`/`retry_min_wait`/`retry_max_wait`
  reintentan la subida de un fragmento o fichero (con [tenacity](https://github.com/jd/tenacity) y
  espera exponencial) cuando la petición falla por tiempo agotado o error de conexión, el fallo
  esperable cuando un fragmento sigue siendo demasiado grande o lento para el servidor. Las
  respuestas de error HTTP (fallos de validación) nunca se reintentan, porque un reintento no puede
  arreglarlas.
- **Subida de paquetes:** `client.get_uploader()` devuelve el cargador adecuado a la versión del
  servidor (`HTTPUploader` en v1, `TusUploader` en v2, con reanudación).

---

## Autenticación

- **Token de acceso estático:** `access_token="<token>"`, enviado como cabecera `Token` en cada
  llamada a la API.
- **Usuario y contraseña:** `user_name`/`user_password`, usados tanto para la autenticación básica o
  de sesión de la API como para el inicio de sesión por cookie requerido por la solución de
  importación de localizaciones y despliegues.
- **Inicio de sesión para las vistas web clásicas:** `APIClientBase.session_login()` gestiona de
  forma transparente el intercambio de token y cookie CSRF (incluido un recurso de último paso que
  extrae el token del HTML cuando la cookie no se establece como se espera), de modo que los
  componentes de escritura anteriores pueden autenticarse contra el formulario de login de Django.

---

## Gestión de errores

- **Tipos de excepción asignados:** `err.NotFoundError`, `err.BadRequestError`,
  `err.UnauthorizedError`, `err.ForbiddenError`, `err.ConflictError`, `err.UnprocessableEntityError`
  y los genéricos `err.ServerError`/`err.APIError`, elegidos según el código de estado de la
  respuesta.
- **Detalles reales del error del servidor, no solo un código de estado:** cuando el servidor incluye
  errores de validación estructurados (errores de formularios de Django, un informe de validación de
  tabla de [frictionless](https://framework.frictionlessdata.io/) incrustado como JSON para un widget
  JS, ...), el SDK los extrae y los incluye en el mensaje de la excepción en lugar de mostrar un
  aviso genérico.
- **Nunca falla ante una respuesta inesperada que no sea JSON:** un error genuino del servidor sin
  gestionar (una página de error HTML en lugar del cuerpo JSON esperado) se detecta y se convierte en
  un `err.APIError` claro con un fragmento del texto, en lugar de un opaco `JSONDecodeError`.

---

## Pruebas

- **Tres capas de pruebas:** `unit` (completamente simuladas, sin red), `integration` (respuestas
  HTTP simuladas que ejercitan más parte del conjunto) y `e2e` (pruebas de humo contra una instancia
  real de Trapper, con activación explícita mediante `WILDINTEL_SMOKE_ENABLED=1`). Consulta
  [Pruebas](testing.md).
- **Una clase base de pruebas compartida** (`ComponentUnitTestBase`) ejercita los seis patrones de
  acceso de forma coherente en todos los componentes, de modo que un componente nuevo obtiene esa
  cobertura sin esfuerzo.
