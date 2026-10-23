# Sistema Multi-Agente: Checagem de Fatos ao Vivo Baseada Exclusivamente em Bancos de Dados Públicos Oficiais do Brasil

---

## 1. Princípio Fundamental de Arquitetura

O sistema é desenhado sob o princípio de **Falsificabilidade por Registro Primário do Estado**.
- **PROIBIÇÃO DE JORNAIS E MÍDIAS**: Fica terminantemente vetado o uso de sites de notícias, tablóides ou portais (como JOTA, Folha, G1, O Globo, Estadão, blogs, ou redes sociais). A imprensa não é fonte primária do Estado; qualquer informação secundária introduz viés editorial ou interpretação de terceiros.
- **USO EXCLUSIVO DE BASES PÚBLICAS**: Toda e qualquer auditoria é ancorada diretamente nos bancos de dados, APIs abertas, diários oficiais e repositórios de microdados mantidos pelos órgãos do Estado Brasileiro.

---

## 2. Mapa do Fluxo Multi-Agente

```
[Declaração do Debate em Tempo Real]
                │
                ▼
      ┌──────────────────┐
      │  Agente Triage   │ ──► [Subjetivo / Opinião pura] ──► Etiqueta: 'Não Verificável por Fonte Oficial'
      │   & Desacoplador │
      └─────────┬────────┘
                │ Parâmetros: Entidade, Métrica, Ano, Esfera
                ▼
      ┌──────────────────┐
      │   Orquestrador   │
      │   de Conectores  │
      └─────────┬────────┘
                ├───► [Agente BCB / SGS] ──► API Oficial Banco Central (Selic, IPCA, Dívida, Câmbio)
                ├───► [Agente IBGE / SIDRA] ──► API SIDRA/Agregados (PNAD Contínua, Desemprego, Censo)
                ├───► [Agente Transparência CGU] ──► API Portal da Transparência (Despesas Federais, CEIS)
                ├───► [Agente Tesouro / Siconfi] ──► API Siconfi/STN (RGF, RREO, Dívidas e Despesas de Municípios e Estados)
                ├───► [Agente Compras / PNCP] ──► API Portal Nacional de Contratações Públicas (Licitações e Contratos)
                ├───► [Agente Legislativo Federal] ──► APIs Câmara/Senado (Votações Nominais, Presença, Cota Parlamentar)
                ├───► [Agente IPEA / Ipeadata] ──► API Ipeadata (Séries Históricas de Pobreza, Homicídios, Saneamento)
                ├───► [Agente TSE Oficial] ──► API DivulgaCandContas (Bens declarados, Receitas, Candidaturas)
                ├───► [Agente Diários Oficiais] ──► API Querido Diário / OKBR (Decretos, Leis, Atos Municipais)
                └───► [Agente Microdados INEP/DATASUS] ──► Banco Colunar Imutável DuckDB/Parquet (Censo Escolar)
                │
                ▼ Tabelas Tidy Data / Respostas JSON Oficiais Brutas
      ┌──────────────────┐
      │  Agente Auditor  │ ◄── Regras de Falsificabilidade & Código de Ética FENAJ
      │ & Síntese Rápida │
      └─────────┬────────┘
                ▼
  [Flash Report: ETIQUETA + DADO BRUTO + LINK OFICIAL DIRETO + AUDITORIA SHA-256 + SÍNTESE]
```

---

## 3. Catálogo Completo dos 10 Conectores de Bancos Públicos Oficiais

1. **Banco Central do Brasil (`BancoCentralSGSConnector`)**:
   - **Banco:** Sistema Gerenciador de Séries Temporais (SGS).
   - **API:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados`
   - **Variáveis:** Taxa Selic (432), IPCA acumulado 12 meses (13522), Câmbio (1), Dívida Pública Líquida / PIB (4505).

2. **IBGE / SIDRA (`IBGESidraConnector`)**:
   - **Banco:** Sistema IBGE de Recuperação Automática (SIDRA).
   - **API:** `https://apisidra.ibge.gov.br/values`
   - **Variáveis:** Taxa de Desocupação / Emprego PNAD Contínua (Tabela 4099), Inflação IPCA por subitem (Tabela 1737), População e Censo.

3. **Portal da Transparência do Governo Federal (`PortalTransparenciaFederalConnector`)**:
   - **Banco:** SIAFI / SIASG / Siape (CGU).
   - **API:** `https://api.portaldatransparencia.gov.br/api-de-dados`
   - **Variáveis:** Execução da despesa por ministério, emendas parlamentares empenhadas/pagas, sanções e empresas inidôneas (CEIS/CNEP).

4. **Secretaria do Tesouro Nacional / Siconfi (`TesouroNacionalSiconfiConnector`)**:
   - **Banco:** Sistema de Informações Contábeis e Fiscais do Setor Público Brasileiro (Siconfi).
   - **API:** `https://apidatalake.tesouro.gov.br/ords/siconfi/tt`
   - **Variáveis:** Relatório de Gestão Fiscal (RGF - limites de gastos com pessoal e dívida), Declaração de Contas Anuais (DCA - despesas municipais e estaduais por função).

5. **Portal Nacional de Contratações Públicas (`PNCPContratacoesConnector`)**:
   - **Banco:** PNCP (Governo Federal / Lei nº 14.133/2021).
   - **API:** `https://pncp.gov.br/api/pncp/v1`
   - **Variáveis:** Contratos administrativos, atas de registro de preços, dispensas de licitação e compras públicas homologadas em todos os entes.

6. **Congresso Nacional - Câmara dos Deputados e Senado (`LegislativoFederalConnector`)**:
   - **Banco:** Dados Abertos do Poder Legislativo.
   - **APIs:** `https://dadosabertos.camara.leg.br/api/v2` e `https://legis.senado.leg.br/dadosabertos`
   - **Variáveis:** Votações nominais em plenário (quem votou 'sim'/'não'), presenças e faltas, despesas com a Cota Parlamentar (CEAP).

7. **IPEA / Ipeadata (`IpeadataConnector`)**:
   - **Banco:** Repositório Estatístico e Macroeconômico do Instituto de Pesquisa Econômica Aplicada.
   - **API:** `http://www.ipeadata.gov.br/api/odata4`
   - **Variáveis:** Séries de homicídios e segurança pública, pobreza, saneamento básico, desigualdade (Gini).

8. **Tribunal Superior Eleitoral (`TSEOficialConnector`)**:
   - **Banco:** DivulgaCandContas / Dados Abertos do TSE.
   - **API:** `https://divulgacandcontas.tse.jus.br/divulga/rest/v1`
   - **Variáveis:** Declarações de bens dos candidatos, certidões eleitorais, histórico de candidaturas e receitas de campanha.

9. **Diários Oficiais Municipais e Estaduais (`QueridoDiarioConnector`)**:
   - **Banco:** Gazetas oficiais abertas (Open Knowledge Brasil).
   - **API:** `https://queridodiario.ok.org.br/api/gazettes`
   - **Variáveis:** Textos brutos de decretos, exonerações, contratações e atos de prefeitos e governadores.

10. **Microdados Locais Imutáveis (`BaseImutavelLocalConnector`)**:
    - **Banco:** Microdados do Censo Escolar da Educação Básica (INEP) e DATASUS.
    - **Motor:** Arquivos Parquet consultados localmente via DuckDB (`PRAGMA read_only=true`).
    - **Variáveis:** Número de matrículas por escola/município, escolas com saneamento/internet, corpo docente.
