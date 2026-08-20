# Painel Contábil e de Auditorias Fiscais

Aplicação Streamlit para uma primeira camada de acompanhamento de obrigações fiscais, análise de documentos fiscais, cruzamentos e identificação de possíveis anomalias. O painel contempla os regimes **Simples Nacional**, **Lucro Presumido** e **Lucro Real** como classificações de análise; ele não substitui a apuração oficial nem a revisão do contador responsável.

## Funcionalidades

O aplicativo permite importar um arquivo Excel, selecionar o regime tributário, filtrar notas por período, status e CFOP, acompanhar obrigações, localizar chaves NF-e duplicadas, identificar impostos superiores ao valor do documento, sinalizar documentos cancelados com valor econômico e detectar obrigações vencidas sem entrega registrada. Também permite exportar notas filtradas e achados de auditoria em Excel.

## Formato do Excel

O arquivo pode conter várias abas. Abas cujo nome contenha `obrig`, `fiscal` ou `declar` são tratadas como obrigações. As demais são avaliadas como notas fiscais quando possuem colunas compatíveis.

| Grupo | Colunas aceitas |
|---|---|
| Notas fiscais | `chave_nfe`, `data_emissao`, `cnpj_emitente`, `cnpj_destinatario`, `valor_total`, `valor_icms`, `valor_pis`, `valor_cofins`, `cfop`, `status` |
| Obrigações | `obrigacao`, `periodo`, `vencimento`, `entrega`, `status`, `valor_declarado` |

Os nomes técnicos e os rótulos em português são aceitos. Colunas ausentes são criadas vazias para preservar o funcionamento do painel, mas a qualidade da análise depende do preenchimento correto.

## Execução local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

No Windows, ative o ambiente com `.venv\\Scripts\\activate`.

## Publicação no Streamlit Community Cloud

1. Crie um repositório público ou privado no GitHub e envie `app.py`, `requirements.txt` e este `README.md`.
2. Acesse [share.streamlit.io](https://share.streamlit.io/) e entre com sua conta GitHub.
3. Selecione o repositório, a branch e o arquivo principal `app.py`.
4. Clique em **Deploy**.
5. Depois da implantação, confirme a URL pública e teste o upload de um Excel anonimizado.

Não inclua dados pessoais, certificados digitais, tokens, senhas ou arquivos fiscais reais no repositório. Para produção, avalie autenticação, controle de acesso, armazenamento seguro e trilhas de logs antes de disponibilizar informações contábeis ou fiscais.

## Próximas evoluções recomendadas

A próxima etapa deve parametrizar regras por UF, regime e período de apuração, incorporar tabelas oficiais e layouts dos sistemas utilizados pela empresa, adicionar conciliação entre documentos de entrada e saída, permitir revisão manual dos achados e registrar uma trilha de auditoria com usuário, data, regra e decisão.
