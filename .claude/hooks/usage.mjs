// Lectura del uso de tokens del sobre de Agent. Módulo aparte porque lo cargan tanto el
// hook como los tests, y el hook, al importarse, se queda esperando stdin.

/**
 * Uso de tokens, leyendo **rutas conocidas** del sobre.
 *
 * Antes se barría el objeto entero recogiendo toda clave que dijera "token", y eso tenía
 * dos fallos que A0 destapó: el mapa era plano, así que `usage.iterations[]` pisaba las
 * claves de arriba y con varias iteraciones se reportaba la última en vez del total; y la
 * suma de respaldo sumaba campos solapados, porque `thinking_tokens` está **dentro** de
 * `output_tokens` y `ephemeral_*` dentro de `cache_creation_input_tokens`.
 *
 * `usage_details` se queda solo con las cuatro partes disjuntas, y su `total` es la suma
 * de esas cuatro y de nada más. Lo que se solapa se manda como metadata, donde informa
 * sin contaminar la aritmética del coste.
 */
export function usageOf(toolResponse) {
  const u = toolResponse?.usage ?? {};
  const input = u.input_tokens ?? 0;
  const output = u.output_tokens ?? 0;
  const cacheRead = u.cache_read_input_tokens ?? 0;
  const cacheWrite = u.cache_creation_input_tokens ?? 0;

  const details = {
    input,
    output,
    cache_read_input_tokens: cacheRead,
    cache_creation_input_tokens: cacheWrite,
    total: input + output + cacheRead + cacheWrite,
  };

  const extras = {
    thinking_tokens: u.output_tokens_details?.thinking_tokens ?? null,
    ephemeral_5m_input_tokens: u.cache_creation?.ephemeral_5m_input_tokens ?? null,
    ephemeral_1h_input_tokens: u.cache_creation?.ephemeral_1h_input_tokens ?? null,
    iterations: Array.isArray(u.iterations) ? u.iterations.length : null,
    service_tier: u.service_tier ?? null,
    speed: u.speed ?? null,
    // El total que declara el harness. Si no cuadra con la suma disjunta, el sobre cambió
    // de forma y conviene verlo en Langfuse en vez de descubrirlo meses después.
    reported_total: toolResponse?.totalTokens ?? null,
  };

  return { details, extras };
}
