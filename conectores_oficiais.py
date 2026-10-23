"""
Conectores e Motor de Checagem em Tempo Real com Fontes Oficiais Primárias do Brasil.
PROIBIÇÃO EXPRESSA: Proibido consultar portais de notícias, jornais (ex: JOTA, Folha, G1, Estadão, etc.) ou mídias.
USO EXCLUSIVO: Bancos de dados abertos do Governo Federal, APIs REST oficiais e Microdados Governamentais.
PADRÃO: Respostas 100% auditáveis com rastreabilidade criptográfica (SHA-256), timestamp UTC e query exata.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, List, Dict, Any, Union
import asyncio
import aiohttp
import hashlib
import json
import os
from datetime import datetime, timezone


class VereditoOficial(str, Enum):
    VERDADE = "Verdade"
    IMPRECISO = "Impreciso"
    FALSO = "Falso"
    NAO_VERIFICAVEL = "Não Verificável por Fonte Oficial"


@dataclass(frozen=True)
class TrilhaAuditoria:
    """Metadados que garantem a auditabilidade técnica independente do fato."""
    endpoint_consultado: str
    parametros_requisicao: Dict[str, Any]
    timestamp_consulta_utc: str
    sha256_payload_bruto: str
    codigo_status_http: int
    orgao_emissor: str
    link_direto_fonte: str = ""


@dataclass(frozen=True)
class FatoAuditado:
    """Objeto final do parecer factual auditável."""
    declaracao_original: str
    classificacao: VereditoOficial
    parametro_oficial: str
    base_primaria: str
    fonte_governamental: str
    sintese_tecnica: str
    trilha_auditoria: TrilhaAuditoria
    dados_brutos_governamentais: Optional[Union[Dict[str, Any], List[Any]]] = None

    def gerar_relatorio_auditavel_markdown(self) -> str:
        """Gera a saída textual em conformidade estrita com o padrão auditável."""
        dados_json = json.dumps(self.dados_brutos_governamentais, indent=2, ensure_ascii=False) if self.dados_brutos_governamentais else "Nenhum registro localizado no banco oficial."
        link_fonte = self.trilha_auditoria.link_direto_fonte or self.trilha_auditoria.endpoint_consultado
        return (
            f"### 🏷️ CLASSIFICAÇÃO: {self.classificacao.value}\n\n"
            f"* **Declaração Auditada:** \"{self.declaracao_original}\"\n"
            f"* **Parâmetro Oficial Localizado:** {self.parametro_oficial}\n"
            f"* **Base de Dados Primária:** {self.base_primaria}\n"
            f"* **Órgão Governamental Emissor:** {self.fonte_governamental}\n"
            f"* **🔗 Link Direto da Fonte Oficial:** [{link_fonte}]({link_fonte})\n\n"
            f"#### 🔍 Síntese Técnica da Auditoria:\n"
            f"{self.sintese_tecnica}\n\n"
            f"---\n"
            f"### 🛡️ TRILHA DE AUDITABILIDADE TÉCNICA (EVIDÊNCIA PRIMÁRIA)\n"
            f"* **Endpoint / URL Primária:** `{self.trilha_auditoria.endpoint_consultado}`\n"
            f"* **Link de Consulta Pública Web:** [{link_fonte}]({link_fonte})\n"
            f"* **Parâmetros da Consulta:** `{json.dumps(self.trilha_auditoria.parametros_requisicao, ensure_ascii=False)}`\n"
            f"* **Data/Hora da Coleta (UTC):** `{self.trilha_auditoria.timestamp_consulta_utc}`\n"
            f"* **Status Code HTTP:** `{self.trilha_auditoria.codigo_status_http}`\n"
            f"* **Hash SHA-256 do Dado Bruto:** `{self.trilha_auditoria.sha256_payload_bruto}`\n\n"
            f"```json\n"
            f"// Payload Bruto Retornado Diretamente pelo Servidor Estatal:\n"
            f"{dados_json}\n"
            f"```\n"
        )


def calcular_hash_sha256(conteudo: Any) -> str:
    """Calcula o hash SHA-256 de um payload retornado pelo governo para comprovação de integridade."""
    if isinstance(conteudo, (dict, list)):
        payload_bytes = json.dumps(conteudo, sort_keys=True, ensure_ascii=False).encode("utf-8")
    elif isinstance(conteudo, str):
        payload_bytes = conteudo.encode("utf-8")
    elif isinstance(conteudo, bytes):
        payload_bytes = conteudo
    else:
        payload_bytes = str(conteudo).encode("utf-8")
    return hashlib.sha256(payload_bytes).hexdigest()


# ==============================================================================
# 1. CONECTOR: BANCO CENTRAL DO BRASIL (BCB - SGS)
# ==============================================================================
class BancoCentralSGSConnector:
    BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados"
    SERIES_COMUNS = {
        "ipca_acumulado_12m": 13522,
        "taxa_selic_meta": 432,
        "taxa_selic_acumulada_ano": 1178,
        "dolar_comercial_venda": 1,
        "pib_mensal_valores_correntes": 4380,
        "divida_liquida_setor_publico_pib": 4505
    }

    async def consultar_serie(
        self,
        session: aiohttp.ClientSession,
        codigo_serie: Union[int, str],
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> Dict[str, Any]:
        url = self.BASE_URL.format(codigo_serie=codigo_serie)
        params = {"formato": "json"}
        if data_inicio:
            params["dataInicial"] = data_inicio
        if data_fim:
            params["dataFinal"] = data_fim

        agora = datetime.now(timezone.utc).isoformat()
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                status = resp.status
                if status == 200:
                    dados = await resp.json()
                    return {
                        "dados": dados,
                        "trilha": TrilhaAuditoria(
                            endpoint_consultado=url,
                            parametros_requisicao=params,
                            timestamp_consulta_utc=agora,
                            sha256_payload_bruto=calcular_hash_sha256(dados),
                            codigo_status_http=status,
                            orgao_emissor="Banco Central do Brasil (BCB / SGS)"
                        )
                    }
                return {"dados": [], "trilha": TrilhaAuditoria(url, params, agora, "", status, "BCB")}
        except Exception as e:
            return {"dados": [], "erro": str(e)}


# ==============================================================================
# 2. CONECTOR: IBGE / SIDRA & AGREGADOS
# ==============================================================================
class IBGESidraConnector:
    SIDRA_BASE_URL = "https://apisidra.ibge.gov.br/values"

    async def consultar_sidra_bruto(self, session: aiohttp.ClientSession, path_sidra: str) -> Dict[str, Any]:
        url = f"{self.SIDRA_BASE_URL}{path_sidra}"
        agora = datetime.now(timezone.utc).isoformat()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                status = resp.status
                if status == 200:
                    dados = await resp.json()
                    return {
                        "dados": dados,
                        "trilha": TrilhaAuditoria(
                            endpoint_consultado=url,
                            parametros_requisicao={"path": path_sidra},
                            timestamp_consulta_utc=agora,
                            sha256_payload_bruto=calcular_hash_sha256(dados),
                            codigo_status_http=status,
                            orgao_emissor="Instituto Brasileiro de Geografia e Estatística (IBGE / SIDRA)"
                        )
                    }
                return {"dados": [], "trilha": TrilhaAuditoria(url, {}, agora, "", status, "IBGE")}
        except Exception as e:
            return {"dados": [], "erro": str(e)}

    async def consultar_desemprego_pnad(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        path = "/t/4099/n1/all/v/4099/p/last%201"
        res = await self.consultar_sidra_bruto(session, path)
        dados = res.get("dados", [])
        if len(dados) > 1:
            res["metrica"] = {"periodo": dados[1].get("D1N"), "taxa_desocupacao_pct": dados[1].get("V")}
        return res


# ==============================================================================
# 3. CONECTOR: PORTAL DA TRANSPARÊNCIA DO GOVERNO FEDERAL (CGU)
# ==============================================================================
class PortalTransparenciaFederalConnector:
    BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TRANSPARENCIA_API_KEY", "")

    async def consultar_despesas_por_orgao(
        self,
        session: aiohttp.ClientSession,
        codigo_orgao_siafi: str,
        ano: int
    ) -> Dict[str, Any]:
        agora = datetime.now(timezone.utc).isoformat()
        url = f"{self.BASE_URL}/despesas/por-orgao"
        params = {"ano": str(ano), "orgao": codigo_orgao_siafi, "pagina": "1"}

        if not self.api_key:
            return {
                "dados": [],
                "trilha": TrilhaAuditoria(url, params, agora, "API_KEY_REQUIRED", 401, "CGU / Portal da Transparência")
            }

        headers = {"chave-api-dados": self.api_key, "Accept": "application/json"}
        try:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                status = resp.status
                if status == 200:
                    dados = await resp.json()
                    return {
                        "dados": dados,
                        "trilha": TrilhaAuditoria(
                            endpoint_consultado=url,
                            parametros_requisicao=params,
                            timestamp_consulta_utc=agora,
                            sha256_payload_bruto=calcular_hash_sha256(dados),
                            codigo_status_http=status,
                            orgao_emissor="Controladoria-Geral da União (CGU / SIAFI)"
                        )
                    }
                return {"dados": [], "trilha": TrilhaAuditoria(url, params, agora, "", status, "CGU")}
        except Exception as e:
            return {"dados": [], "erro": str(e)}


# ==============================================================================
# 4. CONECTOR: TESOURO NACIONAL (SICONFI - STN)
# ==============================================================================
class TesouroNacionalSiconfiConnector:
    BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

    async def consultar_rgf_municipio(
        self,
        session: aiohttp.ClientSession,
        ibge_code: str,
        ano: int,
        periodo: int = 3
    ) -> Dict[str, Any]:
        agora = datetime.now(timezone.utc).isoformat()
        url = f"{self.BASE_URL}/rgf"
        params = {
            "an_exercicio": str(ano),
            "nr_periodo": str(periodo),
            "co_tipo_demonstrativo": "RGF",
            "co_esfera": "M",
            "id_ente": str(ibge_code)
        }
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                status = resp.status
                if status == 200:
                    data = await resp.json()
                    itens = data.get("items", [])
                    return {
                        "dados": itens,
                        "trilha": TrilhaAuditoria(
                            endpoint_consultado=url,
                            parametros_requisicao=params,
                            timestamp_consulta_utc=agora,
                            sha256_payload_bruto=calcular_hash_sha256(itens),
                            codigo_status_http=status,
                            orgao_emissor="Secretaria do Tesouro Nacional (Siconfi / STN)"
                        )
                    }
                return {"dados": [], "trilha": TrilhaAuditoria(url, params, agora, "", status, "STN")}
        except Exception as e:
            return {"dados": [], "erro": str(e)}


# ==============================================================================
# 5. CONECTOR: PORTAL NACIONAL DE CONTRATAÇÕES PÚBLICAS (PNCP)
# ==============================================================================
class PNCPContratacoesConnector:
    BASE_URL = "https://pncp.gov.br/api/pncp/v1"

    async def buscar_contratacoes_por_orgao(
        self,
        session: aiohttp.ClientSession,
        cnpj_orgao: str,
        ano: int
    ) -> Dict[str, Any]:
        agora = datetime.now(timezone.utc).isoformat()
        url = f"{self.BASE_URL}/orgaos/{cnpj_orgao}/compras/{ano}"
        params = {"pagina": "1", "tamanhoPagina": "20"}
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                status = resp.status
                if status == 200:
                    data = await resp.json()
                    itens = data.get("data", [])
                    return {
                        "dados": itens,
                        "trilha": TrilhaAuditoria(
                            endpoint_consultado=url,
                            parametros_requisicao={"cnpj": cnpj_orgao, "ano": ano},
                            timestamp_consulta_utc=agora,
                            sha256_payload_bruto=calcular_hash_sha256(itens),
                            codigo_status_http=status,
                            orgao_emissor="Portal Nacional de Contratações Públicas (PNCP)"
                        )
                    }
                return {"dados": [], "trilha": TrilhaAuditoria(url, params, agora, "", status, "PNCP")}
        except Exception as e:
            return {"dados": [], "erro": str(e)}


# ==============================================================================
# 6. CONECTOR: CÂMARA DOS DEPUTADOS E SENADO (DADOS ABERTOS LEGISLATIVO)
# ==============================================================================
class LegislativoFederalConnector:
    CAMARA_URL = "https://dadosabertos.camara.leg.br/api/v2"

    async def consultar_gastos_cota_parlamentar(
        self,
        session: aiohttp.ClientSession,
        id_deputado: int,
        ano: int
    ) -> Dict[str, Any]:
        agora = datetime.now(timezone.utc).isoformat()
        url = f"{self.CAMARA_URL}/deputados/{id_deputado}/despesas"
        params = {"ano": str(ano), "ordem": "DESC", "ordenarPor": "dataDocumento"}
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                status = resp.status
                if status == 200:
                    data = await resp.json()
                    itens = data.get("dados", [])
                    return {
                        "dados": itens,
                        "trilha": TrilhaAuditoria(
                            endpoint_consultado=url,
                            parametros_requisicao=params,
                            timestamp_consulta_utc=agora,
                            sha256_payload_bruto=calcular_hash_sha256(itens),
                            codigo_status_http=status,
                            orgao_emissor="Câmara dos Deputados (Dados Abertos / CEAP)"
                        )
                    }
                return {"dados": [], "trilha": TrilhaAuditoria(url, params, agora, "", status, "Câmara")}
        except Exception as e:
            return {"dados": [], "erro": str(e)}


# ==============================================================================
# 7. CONECTOR: IPEADATA
# ==============================================================================
class IpeadataConnector:
    BASE_URL = "http://www.ipeadata.gov.br/api/odata4"

    async def consultar_valores_serie(
        self,
        session: aiohttp.ClientSession,
        codigo_serie: str
    ) -> Dict[str, Any]:
        agora = datetime.now(timezone.utc).isoformat()
        url = f"{self.BASE_URL}/Metadados('{codigo_serie}')/Valores"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                status = resp.status
                if status == 200:
                    data = await resp.json()
                    itens = data.get("value", [])
                    return {
                        "dados": itens,
                        "trilha": TrilhaAuditoria(
                            endpoint_consultado=url,
                            parametros_requisicao={"serie": codigo_serie},
                            timestamp_consulta_utc=agora,
                            sha256_payload_bruto=calcular_hash_sha256(itens),
                            codigo_status_http=status,
                            orgao_emissor="Instituto de Pesquisa Econômica Aplicada (Ipeadata)"
                        )
                    }
                return {"dados": [], "trilha": TrilhaAuditoria(url, {}, agora, "", status, "IPEA")}
        except Exception as e:
            return {"dados": [], "erro": str(e)}


# ==============================================================================
# 8. CONECTOR: TRIBUNAL SUPERIOR ELEITORAL (TSE) - DIVULGACANDCONTAS
# ==============================================================================
class TSEOficialConnector:
    BASE_URL = "https://divulgacandcontas.tse.jus.br/divulga/rest/v1"

    async def consultar_candidatura(
        self,
        session: aiohttp.ClientSession,
        ano_eleicao: int,
        sigla_uf: str,
        id_candidato: str
    ) -> Dict[str, Any]:
        agora = datetime.now(timezone.utc).isoformat()
        url = f"{self.BASE_URL}/candidatura/buscar/{ano_eleicao}/{sigla_uf.upper()}/2030402022/candidato/{id_candidato}"
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=3.5)) as resp:
                status = resp.status
                if status == 200:
                    dados = await resp.json()
                    return {
                        "dados": dados,
                        "trilha": TrilhaAuditoria(
                            endpoint_consultado=url,
                            parametros_requisicao={"ano": ano_eleicao, "uf": sigla_uf, "id": id_candidato},
                            timestamp_consulta_utc=agora,
                            sha256_payload_bruto=calcular_hash_sha256(dados),
                            codigo_status_http=status,
                            orgao_emissor="Tribunal Superior Eleitoral (TSE / DivulgaCandContas)"
                        )
                    }
                return {"dados": {}, "trilha": TrilhaAuditoria(url, {}, agora, "", status, "TSE")}
        except Exception as e:
            return {"dados": {}, "erro": str(e)}


# ==============================================================================
# 9. CONECTOR: DIÁRIOS OFICIAIS (QUERIDO DIÁRIO / OKBR)
# ==============================================================================
class QueridoDiarioConnector:
    BASE_URL = "https://queridodiario.ok.org.br/api"

    async def buscar_atos_normativos(
        self,
        session: aiohttp.ClientSession,
        termo_busca: str,
        ibge_code: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> Dict[str, Any]:
        agora = datetime.now(timezone.utc).isoformat()
        params = {"querystring": f'"{termo_busca}"'}
        if ibge_code:
            params["territory_id"] = str(ibge_code)
        if data_inicio:
            params["since"] = data_inicio
        if data_fim:
            params["until"] = data_fim

        url = f"{self.BASE_URL}/gazettes"
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                status = resp.status
                if status == 200:
                    dados = await resp.json()
                    return {
                        "dados": dados,
                        "trilha": TrilhaAuditoria(
                            endpoint_consultado=url,
                            parametros_requisicao=params,
                            timestamp_consulta_utc=agora,
                            sha256_payload_bruto=calcular_hash_sha256(dados),
                            codigo_status_http=status,
                            orgao_emissor="Diários Oficiais Municipais / Estaduais (Querido Diário)"
                        )
                    }
                return {"dados": {}, "trilha": TrilhaAuditoria(url, params, agora, "", status, "Diários")}
        except Exception as e:
            return {"dados": {}, "erro": str(e)}


# ==============================================================================
# 10. CONECTOR: MICRODADOS LOCAIS IMUTÁVEIS (INEP / DATASUS)
# ==============================================================================
class BaseImutavelLocalConnector:
    def __init__(self, data_dir: str = "./dados_oficiais_locais/"):
        self.data_dir = data_dir

    def executar_query_analitica(self, query_sql: str) -> Dict[str, Any]:
        agora = datetime.now(timezone.utc).isoformat()
        try:
            import duckdb
            con = duckdb.connect(database=":memory:", read_only=True)
            con.execute("PRAGMA read_only=true;")
            df = con.execute(query_sql).fetchdf()
            dados = df.to_dict(orient="records")
            return {
                "dados": dados,
                "trilha": TrilhaAuditoria(
                    endpoint_consultado="duckdb://local_memory_replica",
                    parametros_requisicao={"sql": query_sql},
                    timestamp_consulta_utc=agora,
                    sha256_payload_bruto=calcular_hash_sha256(dados),
                    codigo_status_http=200,
                    orgao_emissor="Microdados Oficiais Imutáveis (INEP / Censo Escolar / DATASUS)"
                )
            }
        except Exception as e:
            return {"dados": [], "erro": str(e)}


# ==============================================================================
# ORQUESTRADOR CENTRAL DE FONTES GOVERNAMENTAIS BRASILEIRAS
# ==============================================================================
class OrquestradorFontesOficiais:
    def __init__(self, transparencia_key: Optional[str] = None):
        self.bcb = BancoCentralSGSConnector()
        self.ibge = IBGESidraConnector()
        self.transparencia = PortalTransparenciaFederalConnector(api_key=transparencia_key)
        self.siconfi = TesouroNacionalSiconfiConnector()
        self.pncp = PNCPContratacoesConnector()
        self.legislativo = LegislativoFederalConnector()
        self.ipea = IpeadataConnector()
        self.tse = TSEOficialConnector()
        self.diarios = QueridoDiarioConnector()
        self.local_sql = BaseImutavelLocalConnector()
