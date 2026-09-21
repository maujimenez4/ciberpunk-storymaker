# Ontología de generación de novelas con IA — Árboles y grafos (Mermaid)

**Versión:** 1.0 · **Fecha:** 2026-09-21 · **Documento hermano:** `01-ontologia-novelas-definiciones.md`

Todos los diagramas usan sintaxis Mermaid y se renderizan en GitHub, GitLab, Obsidian, Notion y VS Code con la extensión de Mermaid.

**Índice**

1. Mapa general de capas
2. Árbol taxonómico de clases
3. Árbol por capa (historia, discurso, género, estado, producción)
4. Anatomía estructural de la obra
5. Grafo de relaciones (modelo entidad-relación)
6. Anatomía del personaje
7. Flujo de la información: plantado, revelación, pago, conocimiento
8. Beats obligatorios del romance
9. Composición del paquete de contexto
10. Árbol de calidad: dimensiones, métricas, defectos
11. Pipeline del sistema
12. Ciclo de vida de una escena

---

## 1. Mapa general de capas

```mermaid
flowchart TD
  ONT["Ontología del dominio<br/>novela generada por IA"]
  ONT --> H["Capa de HISTORIA<br/>qué ocurre y por qué"]
  ONT --> D["Capa de DISCURSO<br/>cómo se cuenta"]
  ONT --> G["Capa de GÉNERO<br/>qué espera el lector"]
  ONT --> E["Capa de ESTADO<br/>qué es verdad en T"]
  ONT --> P["Capa de PRODUCCIÓN<br/>cómo se fabrica y acepta"]

  H --> H1["Estructura, agentes,<br/>mundo, eventos"]
  D --> D1["POV, voz, ritmo,<br/>tipografía"]
  G --> G1["Beats, tropos,<br/>nivel de calor"]
  E --> E1["Ledger, contexto,<br/>memoria"]
  P --> P1["Prompts, métricas,<br/>puertas, versiones"]
```

---

## 2. Árbol taxonómico de clases

```mermaid
flowchart LR
  R["Clase raíz"]

  R --> A["EntidadEstructural"]
  R --> B["EntidadNarrativa"]
  R --> C["EntidadDeDiscurso"]
  R --> D["EntidadDeGenero"]
  R --> E["EntidadDeContexto"]
  R --> F["EntidadDeCalidad"]
  R --> G["EntidadDeProduccion"]

  A --> A1["Serie · Obra · Parte<br/>Capitulo · Escena · Beat"]
  B --> B1["Personaje · Relacion<br/>Lugar · Objeto · ReglaDeMundo"]
  B --> B2["Evento · HechoCanon<br/>Plantado · Pago · Revelacion"]
  B --> B3["Premisa · Tema · Conflicto<br/>Arco · Trama · HiloNarrativo"]
  C --> C1["PerfilDeVoz · POV · Focalizacion<br/>Ritmo · EstandarTipografico"]
  D --> D1["BeatDeGenero · Tropo<br/>NivelDeCalor · Subgenero"]
  E --> E1["PaqueteDeContexto · Ledger<br/>EstadoEnT · MuestraAncla"]
  F --> F1["DimensionDeCalidad · Metrica<br/>Defecto · PuertaDeCalidad"]
  G --> G1["Brief · Biblia · Outline<br/>Prompt · Ejecucion · VersionDeTexto"]
```

---

## 3. Árbol por capa

### 3.1 Historia

```mermaid
flowchart TD
  H["HISTORIA"]
  H --> H1["Estructura"]
  H --> H2["Núcleo dramático"]
  H --> H3["Agentes"]
  H --> H4["Mundo"]
  H --> H5["Eventos e información"]

  H1 --> H11["Serie"]
  H1 --> H12["Obra"]
  H1 --> H13["Parte / Acto"]
  H1 --> H14["Capitulo"]
  H1 --> H15["Escena"]
  H1 --> H16["Beat"]

  H2 --> H21["Premisa · Logline"]
  H2 --> H22["Tema"]
  H2 --> H23["Conflicto"]
  H2 --> H24["Arco"]
  H2 --> H25["Trama y subtramas"]

  H3 --> H31["Personaje"]
  H3 --> H32["Relacion"]

  H4 --> H41["Lugar"]
  H4 --> H42["Objeto"]
  H4 --> H43["ReglaDeMundo"]
  H4 --> H44["Cronologia"]

  H5 --> H51["Evento"]
  H5 --> H52["HechoCanon"]
  H5 --> H53["Plantado y Pago"]
  H5 --> H54["Revelacion"]
  H5 --> H55["HiloNarrativo"]
```

### 3.2 Discurso

```mermaid
flowchart TD
  D["DISCURSO"]
  D --> D1["Punto de vista"]
  D --> D2["Voz"]
  D --> D3["Ritmo y textura"]
  D --> D4["Convención editorial"]

  D1 --> D11["Persona: 1ª / 3ª limitada / omnisciente"]
  D1 --> D12["Focalización y esquema de POV"]
  D1 --> D13["Distancia psíquica 1-5"]
  D1 --> D14["Tiempo verbal"]

  D2 --> D21["PerfilDeVoz por personaje"]
  D2 --> D22["Registro y léxico vetado"]
  D2 --> D23["MuestraAncla de prosa aprobada"]

  D3 --> D31["Proporción escena / resumen"]
  D3 --> D32["Densidad de diálogo"]
  D3 --> D33["Longitud de frase y párrafo"]

  D4 --> D41["Raya de diálogo y acotaciones"]
  D4 --> D42["Comillas latinas y sangrías"]
  D4 --> D43["Tratamiento tú / usted"]
```

### 3.3 Género (romance)

```mermaid
flowchart TD
  G["GÉNERO"]
  G --> G1["Contrato con el lector"]
  G --> G2["Convenciones"]
  G --> G3["Restricciones"]

  G1 --> G11["PromesaDeApertura"]
  G1 --> G12["Tipo de final: HEA / HFN"]
  G1 --> G13["La relación es la trama A"]

  G2 --> G21["BeatDeGenero obligatorios"]
  G2 --> G22["Tropo declarado"]
  G2 --> G23["Subgénero"]
  G2 --> G24["EquilibrioDePOV"]

  G3 --> G31["NivelDeCalor"]
  G3 --> G32["Advertencias de contenido"]
  G3 --> G33["Edad mínima y consentimiento"]
```

### 3.4 Estado y contexto

```mermaid
flowchart TD
  E["ESTADO Y CONTEXTO"]
  E --> E1["Fuentes de verdad"]
  E --> E2["Derivación"]
  E --> E3["Ensamblado"]
  E --> E4["Contención de deriva"]

  E1 --> E11["Grafo de canon"]
  E1 --> E12["Ledger de eventos"]
  E1 --> E13["Manuscrito versionado"]
  E1 --> E14["Índice vectorial"]

  E2 --> E21["EstadoEnT de cada personaje"]
  E2 --> E22["Resúmenes en cascada"]
  E2 --> E23["Registro de hilos abiertos"]

  E3 --> E31["PaqueteDeContexto por escena"]
  E3 --> E32["Presupuesto de tokens por capa"]
  E3 --> E33["Recuperación híbrida"]

  E4 --> E41["MuestraAncla de voz"]
  E4 --> E42["Lista negra de n-gramas"]
  E4 --> E43["Curva de tensión planificada"]
```

### 3.5 Producción

```mermaid
flowchart TD
  P["PRODUCCIÓN"]
  P --> P1["Artefactos"]
  P --> P2["Roles de agente"]
  P --> P3["Control"]

  P1 --> P11["Brief"]
  P1 --> P12["Biblia"]
  P1 --> P13["Outline"]
  P1 --> P14["FichaDeEscena"]
  P1 --> P15["VersionDeTexto"]

  P2 --> P21["Arquitecto"]
  P2 --> P22["Planificador de escena"]
  P2 --> P23["Ensamblador de contexto"]
  P2 --> P24["Escritor"]
  P2 --> P25["Continuista"]
  P2 --> P26["Crítico"]
  P2 --> P27["Editor de línea"]
  P2 --> P28["Extractor"]

  P3 --> P31["Prompt versionado"]
  P3 --> P32["Ejecucion con semilla y coste"]
  P3 --> P33["PuertaDeCalidad"]
```

---

## 4. Anatomía estructural de la obra

```mermaid
flowchart TD
  A["Serie"] --> B["Obra<br/>80.000-120.000 palabras"]
  B --> C["Parte / Acto<br/>función estructural"]
  C --> D["Capitulo<br/>2.500-4.000 palabras"]
  D --> E["Escena<br/>800-2.000 palabras<br/>UNIDAD ATÓMICA"]
  E --> F["Beat<br/>acción - reacción"]

  E -.criterio de cierre.-> E1["El valor emocional<br/>cambia de signo"]
  D -.criterio de cierre.-> D1["Corta en tensión<br/>o revelación"]
  C -.criterio de cierre.-> C1["Cambio irreversible<br/>en la situación"]
```

---

## 5. Grafo de relaciones

```mermaid
erDiagram
  OBRA ||--|{ PARTE : contiene
  PARTE ||--|{ CAPITULO : contiene
  CAPITULO ||--|{ ESCENA : contiene
  ESCENA ||--|{ BEAT : contiene

  ESCENA }o--|| LUGAR : ocurre_en
  ESCENA }o--|| PERSONAJE : narrada_desde
  ESCENA ||--|{ EVENTO : dramatiza
  ESCENA }o--o| BEAT_DE_GENERO : cumple
  ESCENA ||--o{ PLANTADO : planta
  ESCENA ||--o{ PLANTADO : paga
  ESCENA ||--o{ REVELACION : revela

  PERSONAJE }o--o{ EVENTO : presencia
  PERSONAJE ||--o{ REVELACION : sabe_desde
  PERSONAJE ||--|| PERFIL_DE_VOZ : tiene_voz
  PERSONAJE }o--o{ RELACION : mantiene
  PERSONAJE ||--o{ OBJETO : posee

  EVENTO ||--o{ EVENTO : causa
  EVENTO ||--o{ HECHO_CANON : establece
  HECHO_CANON ||--o{ HECHO_CANON : contradice

  RELACION ||--|{ ESCENA : evoluciona_en
  ARCO ||--|{ ESCENA : progresa_en
  EJECUCION ||--|| VERSION_DE_TEXTO : produce
```

---

## 6. Anatomía del personaje

```mermaid
flowchart TD
  PJ["Personaje"]

  PJ --> F["PARTE FIJA<br/>vive en la biblia"]
  PJ --> M["PARTE MÓVIL<br/>vive en el ledger"]
  PJ --> V["PerfilDeVoz<br/>entidad separada"]

  F --> F1["Identidad: nombre, edad,<br/>físico, profesión, familia"]
  F --> F2["Psicología profunda"]
  F --> F3["Rol narrativo"]

  F2 --> F21["Herida original"]
  F2 --> F22["Mentira que se cree"]
  F2 --> F23["Deseo consciente"]
  F2 --> F24["Necesidad inconsciente"]
  F2 --> F25["Miedo central"]

  M --> M1["Ubicación y apariencia del día"]
  M --> M2["Estado emocional y heridas"]
  M --> M3["Qué sabe y desde qué escena"]
  M --> M4["Qué oculta y a quién"]

  V --> V1["Léxico propio y muletillas"]
  V --> V2["Sintaxis: longitud de frase"]
  V --> V3["Registro y humor"]
  V --> V4["Temas que evita · cómo miente"]
```

> **Prueba de validez de la voz:** dado un párrafo sin nombres propios, un clasificador debe identificar el POV correcto.

---

## 7. Flujo de la información

```mermaid
flowchart LR
  P["Plantado<br/>escena N"] --> S["Silencio<br/>escenas N+1..M-1"]
  S --> R["Revelación<br/>escena M"]
  R --> G["Pago<br/>escena M o posterior"]
  G --> C["Hilo cerrado"]

  R --> K["Personaje actualiza<br/>sabe_desde"]
  K --> V["Validador:<br/>¿puede usar este dato?"]
  V -->|sí| OK["Diálogo permitido"]
  V -->|no| ERR["Defecto CON-03"]
```

**Derivación del conocimiento:**

```mermaid
flowchart TD
  EV["Evento"] --> T["testigos[]"]
  T --> SD["sabe_desde<br/>personaje + escena"]
  SD --> ST["EstadoEnT<br/>derivado"]
  ST --> CTX["Capa 'Estado en T'<br/>del paquete de contexto"]
  CTX --> ESC["Escritura de la escena"]
  ESC --> VAL["Validador de conocimiento"]
  VAL -->|defecto| ESC
  VAL -->|aprobada| EXT["Extractor de hechos"]
  EXT --> EV
```

---

## 8. Beats obligatorios del romance

```mermaid
flowchart LR
  B1["0-8%<br/>Carencias"] --> B2["8-12%<br/>Encuentro"]
  B2 --> B3["20-25%<br/>Punto de<br/>no retorno"]
  B3 --> B4["25-50%<br/>Diversión<br/>y juegos"]
  B4 --> B5["50%<br/>Punto medio"]
  B5 --> B6["50-70%<br/>La grieta"]
  B6 --> B7["70-80%<br/>Ruptura"]
  B7 --> B8["80-90%<br/>Revelación<br/>interior"]
  B8 --> B9["90-97%<br/>Gran gesto"]
  B9 --> B10["97-100%<br/>HEA / HFN"]
```

**Curva de temperatura de la relación (0-10):**

```mermaid
flowchart LR
  T1["2<br/>Carencias"] --> T2["4<br/>Encuentro"]
  T2 --> T3["5<br/>No retorno"]
  T3 --> T4["7<br/>Intimidad"]
  T4 --> T5["8<br/>Punto medio"]
  T5 --> T6["6<br/>Grieta"]
  T6 --> T7["1<br/>Ruptura"]
  T7 --> T8["5<br/>Revelación"]
  T8 --> T9["9<br/>Gran gesto"]
  T9 --> T10["10<br/>HEA"]
```

> El retroceso del 70-80 % es obligatorio: sin él, el arco romántico avanza en línea recta y el final no se gana.

---

## 9. Composición del paquete de contexto

```mermaid
flowchart TD
  FE["FichaDeEscena"] --> ENS["Ensamblador de contexto<br/>código determinista"]

  BIB["Biblia"] --> C1["Constitucional · 5%"]
  OUT["Outline"] --> C2["Estructural · 10%"]
  GRAFO["Grafo de canon"] --> C3["Canon relevante · 20%"]
  LEDGER["Ledger"] --> C4["Estado en T · 15%"]
  MS["Manuscrito"] --> C5["Continuidad local · 20%"]
  VEC["Índice vectorial"] --> C6["Memoria recuperada · 10%"]
  FE --> C7["Instrucción · 10%"]

  C1 --> ENS
  C2 --> ENS
  C3 --> ENS
  C4 --> ENS
  C5 --> ENS
  C6 --> ENS
  C7 --> ENS

  ENS --> PK["PaqueteDeContexto<br/>+ 10% de reserva"]
  PK --> LLM["Escritor"]
```

**Reglas de ensamblado:** se selecciona y no se acumula · lo importante al principio y al final · filtro estructural antes que similitud semántica · texto literal solo para lo contiguo · lo derivado nunca se escribe a mano.

---

## 10. Árbol de calidad

```mermaid
flowchart TD
  Q["Calidad"]
  Q --> N1["Nivel ESCENA"]
  Q --> N2["Nivel CAPÍTULO"]
  Q --> N3["Nivel MANUSCRITO"]

  N1 --> Q11["Coherencia de canon → CAN-01"]
  N1 --> Q12["Continuidad física y temporal → CON-01, CON-02"]
  N1 --> Q13["Coherencia de conocimiento → CON-03"]
  N1 --> Q14["Consistencia de voz → VOZ-01, VOZ-02"]
  N1 --> Q15["Calidad de prosa → PRO-01, PRO-02"]
  N1 --> Q16["Función dramática → EST-01"]

  N2 --> Q21["Ritmo y variedad"]
  N2 --> Q22["Proporción escena / resumen"]

  N3 --> Q31["Cumplimiento de género → GEN-01, GEN-02"]
  N3 --> Q32["Arco romántico y curva"]
  N3 --> Q33["Cabos sueltos"]
  N3 --> Q34["Contrato con el lector → SEG-01"]
```

**Quién mide qué:**

```mermaid
flowchart LR
  A["Métricas automáticas"] --> A1["Repetición de n-gramas<br/>Tics corporales<br/>Variedad sintáctica<br/>Deriva de estilo"]
  B["Juez LLM con rúbrica"] --> B1["Función dramática<br/>Subtexto<br/>Satisfacción del beat"]
  C["Editor humano"] --> C1["Voz, gusto,<br/>decisión final"]
  A1 --> D["PuertaDeCalidad"]
  B1 --> D
  C1 --> D
  D -->|defecto| E["Reparación dirigida<br/>máximo 2 reintentos"]
  D -->|aprobada| F["Siguiente fase"]
  E --> D
```

---

## 11. Pipeline del sistema

```mermaid
flowchart TD
  A["Brief: género,<br/>tropo, tono"] --> B["Premisa y logline"]
  B --> C["Biblia:<br/>personajes, mundo, voz"]
  C --> D["Outline por actos<br/>y beats de género"]
  D --> E["FichaDeEscena"]
  E --> F["Ensamblador<br/>de contexto"]
  F --> G["Escritor"]
  G --> H["Continuista<br/>y Crítico"]
  H -->|defecto| G
  H -->|aprobada| I["Extractor:<br/>hechos, estado, hilos"]
  I --> F
  I --> J["Editor de línea"]
  J --> K["Ensamblaje<br/>y auditoría final"]
  K -->|cabos sueltos| D
  K --> L["Manuscrito"]
```

---

## 12. Ciclo de vida de una escena

```mermaid
stateDiagram-v2
  [*] --> Planificada
  Planificada --> EnContexto : ficha completa
  EnContexto --> Redactada : llamada al modelo
  Redactada --> EnValidacion
  EnValidacion --> EnReparacion : defecto bloqueante
  EnReparacion --> Redactada : reintento dirigido
  EnReparacion --> EscaladaAHumano : 2 reintentos fallidos
  EscaladaAHumano --> Redactada : corrección manual
  EnValidacion --> Aprobada : puertas superadas
  Aprobada --> Integrada : hechos extraídos al canon
  Integrada --> Pulida : pase de línea
  Pulida --> [*]
  EnValidacion --> Descartada : escena sin función
  Descartada --> [*]
```