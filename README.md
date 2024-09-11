<h1>Pruebas
Lenguaje largo usando ollama</h1>


<!-- Sección de pruebas con el uso del lenguaje largo a través de ollama -->

<h1> #1. Instalacion </h1>
El primer paso es descargamos [ollama] (https://ollama.com/download/linux) de su pagina web, y ejecutamos el siguiente comando

<!-- Explicación sobre cómo instalar ollama -->

````bash
curl -fsSL https://ollama.com/install.sh | sh
````
<!-- Comando para descargar e instalar ollama usando curl. El script de instalación se ejecuta directamente desde la URL proporcionada. -->

<h1>#2. Correr el servidor</h1>

para iniciar corremos el comando

<!-- Explicación sobre cómo iniciar el servidor de ollama -->

````bash
ollama serve
````
<!-- Comando para iniciar el servidor de ollama. Esto pone en marcha el servicio para que puedas interactuar con él. -->

<h1>#3. Import module IA</h1>
buscamos el modelo a descargar en https://ollama.com/library

<!-- Instrucciones para importar un modelo de inteligencia artificial desde la biblioteca de ollama -->

luego lanzamos el comado, Abrir otra ventana de comando 

<!-- Aquí se indica que se debe abrir una nueva ventana de terminal para ejecutar el siguiente comando -->

````bash
ollama pull tinyllama
````
ollama list me muestra los modelos importados

<!-- Explicación de cómo listar los modelos importados -->

````bash
ollama list
````
<!-- Comando para listar todos los modelos que se han importado en tu sistema. -->

para hacer una pregunta 

<!-- Instrucciones para ejecutar consultas al modelo importado -->

````bash
ollama run tinyllama (se coloca la pregunta aqui)
````
<!-- Comando para ejecutar una consulta al modelo "tinyllama". Reemplaza "(se coloca la pregunta aqui)" con la pregunta que deseas hacer. -->

comandos aqui = https://github.com/ollama/ollama/blob/main/docs/api.md

-X = metodo que quiero usar

<!-- Indica que los comandos adicionales están documentados en el enlace proporcionado, y "X" representa el método que quieres usar -->

````bash
curl http://localhost:11434/api/generate -d '{
  "model": "tinyllama",
  "prompt": "Why is the sky blue?"
}'
````

<!-- Comando curl para enviar una solicitud POST a la API del servidor local (puerto 11434) con el modelo "tinyllama" y un "prompt" (pregunta). -->

````bash
curl http://localhost:11434/api/generate -d '{
  "model": "tinyllama",
  "prompt": "Why is the sky blue?"
}' -o salida.md
````
<!-- Comando curl similar al anterior, pero con la opción "-o salida.md" para guardar la respuesta de la API en un archivo llamado "salida.md". -->

````bash
curl http://localhost:11434/api/generate -d '{
  "model": "tinyllama",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
````
<!-- Comando curl para enviar una solicitud POST a la API con el modelo "tinyllama" y un "prompt" (pregunta), con la opción `"stream": false` para recibir la respuesta completa en lugar de un flujo de datos. -->

<h1>GroqCloud</h1>

<!-- Sección sobre cómo registrarse y usar GroqCloud -->

Registramos y creamos cuenta si no la tenemos, creamos llave 
Podemos Revisar la documentacion en este apartado https://console.groq.com/docs/quickstart

<!-- Comando para exportar la clave API de GroqCloud como una variable de entorno llamada `GROQ_API_KEY`. -->

Ejemplo:
````bash
export GROQ_API_KEY=TU_API_KEY
````
Revisamos que la llave este bien cargada

````bash
echo $GROQ_API_KEY
````
<!-- Comando para verificar que la variable de entorno `GROQ_API_KEY` ha sido cargada correctamente y muestra su valor. -->

Ejecutamos ya teniendo la clave 

````bash
curl "https://api.groq.com/openai/v1/chat/completions" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${GROQ_API_KEY}" \
  -d '{
         "messages": [
           {
             "role": "user",
             "content": "¿Porque el cielo es Azul?"
           }
         ],
         "model": "llama3-8b-8192",
         "stream": false
       }'
````
<h1>W3 Schols</h1>

<!-- Comando curl para enviar una solicitud POST a la API de GroqCloud con una pregunta en el formato requerido, usando la clave API para autorización. -->