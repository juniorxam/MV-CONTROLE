import streamlit as st
import json
from datetime import datetime
import pandas as pd
from streamlit_local_storage import LocalStorage

# Configuração da página Web
st.set_page_config(page_title="Frango Assado MV - Gestão & Vendas", page_icon="🍗", layout="wide")

# Inicializa LocalStorage
local_storage = LocalStorage()

# Configurações Padrões de Preços (R$)
PRECOS_PADRAO = {
    'PRECO_FRANGO': 60.00,       # Frango Assado (com batata inclusa)
    'PRECO_FAROFA': 5.00,        # Porção de Farofinha
    'PRECO_BATATA_EXTRA': 10.00, # Batata Extra
    'PRECO_REFRIGERANTE': 8.00   # Refri 2L
}

# ==========================================
# FUNÇÕES DE SUPORTE
# ==========================================
def carregar_precos():
    cfgs = local_storage.getItem("mv_precos")
    if cfgs:
        try:
            dados = json.loads(cfgs)
            res = PRECOS_PADRAO.copy()
            res.update(dados)
            return res
        except:
            return PRECOS_PADRAO.copy()
    return PRECOS_PADRAO.copy()

def carregar_historico():
    hist = local_storage.getItem("mv_historico")
    return json.loads(hist) if hist else []

def salvar_historico(historico):
    local_storage.setItem("mv_historico", json.dumps(historico))

# ==========================================
# INTERFACE GRÁFICA
# ==========================================
st.title("🍗 Frango Assado MV")
st.caption("Sistema de Gestão de Vendas, Clientes e Desempenho")

precos_atuais = carregar_precos()
historico_vendas = carregar_historico()

aba_dash, aba1, aba2, aba3, aba4 = st.tabs([
    "📊 Dashboard", 
    "🛒 Nova Venda", 
    "👥 Clientes", 
    "📜 Histórico & Edição", 
    "⚙️ Tabela de Preços"
])

# ------------------------------------------
# ABA DASHBOARD: PAINEL DE DESEMPENHO DOMINICAL
# ------------------------------------------
with aba_dash:
    st.markdown("### 📊 Painel de Vendas por Domingo")
    
    if historico_vendas:
        df = pd.DataFrame(historico_vendas)
        
        # Converte e extrai apenas a data (sem a hora) para agrupar por dia/domingo
        df['data_dt'] = pd.to_datetime(df['data_hora'], format="%d/%m/%Y %H:%M")
        df['data_str'] = df['data_dt'].dt.strftime("%d/%m/%Y")
        
        datas_disponiveis = df['data_str'].unique()
        
        # Filtro de seleção de Domingo/Data
        col_filtro, _ = st.columns([2, 2])
        with col_filtro:
            data_selecionada = st.selectbox("🗓️ Selecione o Domingo/Dia:", datas_disponiveis, index=0)
        
        # Dados do dia selecionado
        df_dia = df[df['data_str'] == data_selecionada]
        
        total_faturado_dia = df_dia['valor_final'].sum()
        total_frangos_dia = df_dia['qtd_frango'].sum()
        total_pedidos_dia = len(df_dia)
        ticket_medio = total_faturado_dia / total_pedidos_dia if total_pedidos_dia > 0 else 0
        
        # Métricas Principais do Dia
        st.markdown(f"#### 🎯 Resumo de {data_selecionada}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Faturamento Total", f"R$ {total_faturado_dia:.2f}")
        m2.metric("🍗 Frangos Vendidos", f"{total_frangos_dia} un.")
        m3.metric("📦 Pedidos Atendidos", f"{total_pedidos_dia}")
        m4.metric("🏷️ Ticket Médio / Pedido", f"R$ {ticket_medio:.2f}")
        
        st.markdown("---")
        
        # Gráfico comparativo entre Domingos
        st.markdown("#### 📈 Comparativo de Faturamento entre Domingos")
        df_agrupado_dia = df.groupby('data_str', as_index=False)['valor_final'].sum()
        df_agrupado_dia.columns = ['Data', 'Faturamento (R$)']
        st.bar_chart(data=df_agrupado_dia, x='Data', y='Faturamento (R$)', height=250)
        
        # Totais de Acompanhamentos no Dia Selecionado
        st.markdown(f"#### 🥣 Itens Acompanhantes Vendidos em {data_selecionada}")
        c_i1, c_i2, c_i3 = st.columns(3)
        c_i1.metric("Farofas Vendidas", f"{df_dia['qtd_farofa'].sum()} porções")
        c_i2.metric("Batatas Extras", f"{df_dia['qtd_batata'].sum()} porções")
        c_i3.metric("Refrigerantes", f"{df_dia['qtd_refri'].sum()} un.")

    else:
        st.info("Nenhuma venda registrada ainda para exibir dados no Dashboard.")

# ------------------------------------------
# ABA 1: NOVA VENDA (COM VALOR EDITÁVEL/DESCONTO)
# ------------------------------------------
with aba1:
    st.markdown("### 📝 Registrar Novo Pedido")
    
    col_c1, col_c2 = st.columns([2, 1])
    with col_c1:
        cliente_nome = st.text_input("Nome do Cliente", placeholder="Ex: João da 407 Norte")
    with col_c2:
        telefone = st.text_input("Telefone / WhatsApp", placeholder="Ex: 63 99297-1557")

    st.markdown("---")
    st.markdown("#### Itens do Pedido")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        qtd_frango = st.number_input("🍗 Frango Assado (c/ Batata)", min_value=0, value=1, step=1)
    with col2:
        qtd_farofa = st.number_input("🥣 Porção de Farofa", min_value=0, value=1, step=1)
    with col3:
        qtd_batata = st.number_input("🥔 Batata Extra", min_value=0, value=0, step=1)
    with col4:
        qtd_refri = st.number_input("🥤 Refrigerante", min_value=0, value=0, step=1)

    # Cálculo do valor base pela tabela
    subtotal = (
        (qtd_frango * precos_atuais['PRECO_FRANGO']) +
        (qtd_farofa * precos_atuais['PRECO_FAROFA']) +
        (qtd_batata * precos_atuais['PRECO_BATATA_EXTRA']) +
        (qtd_refri * precos_atuais['PRECO_REFRIGERANTE'])
    )

    st.markdown("---")
    st.markdown("#### Ajuste de Valor & Promoções")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.metric("Subtotal Padrão", f"R$ {subtotal:.2f}")
    with col_v2:
        valor_final = st.number_input(
            "💰 Valor Final cobrado (Editável para Promoções/Descontos)", 
            min_value=0.0, 
            value=float(subtotal), 
            step=1.0, 
            format="%.2f"
        )

    obs = st.text_input("Observações do Pedido / Promoção", placeholder="Ex: Desconto de vizinho / Promocional 2 frangos")

    if st.button("✅ Confirmar e Finalizar Venda", type="primary", use_container_width=True):
        nova_venda = {
            'id': int(datetime.now().timestamp()),
            'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'cliente': cliente_nome.strip() if cliente_nome.strip() else "Cliente Não Identificado",
            'telefone': telefone.strip(),
            'qtd_frango': qtd_frango,
            'qtd_farofa': qtd_farofa,
            'qtd_batata': qtd_batata,
            'qtd_refri': qtd_refri,
            'subtotal': round(subtotal, 2),
            'valor_final': round(valor_final, 2),
            'observacao': obs
        }
        
        historico_vendas.insert(0, nova_venda)
        salvar_historico(historico_vendas)
        st.success(f"Venda registrada com sucesso! Total: R$ {valor_final:.2f}")
        st.rerun()

# ------------------------------------------
# ABA 2: GESTÃO DE CLIENTES
# ------------------------------------------
with aba2:
    st.markdown("### 👥 Ranking e Histórico por Cliente")
    
    if historico_vendas:
        resumo_clientes = {}
        for v in historico_vendas:
            nome = v['cliente']
            val = v['valor_final']
            if nome in resumo_clientes:
                resumo_clientes[nome]['total_gasto'] += val
                resumo_clientes[nome]['qtd_pedidos'] += 1
                if v['telefone'] and not resumo_clientes[nome]['telefone']:
                    resumo_clientes[nome]['telefone'] = v['telefone']
            else:
                resumo_clientes[nome] = {
                    'total_gasto': val,
                    'qtd_pedidos': 1,
                    'telefone': v.get('telefone', '')
                }

        clientes_ordenados = sorted(resumo_clientes.items(), key=lambda x: x[1]['total_gasto'], reverse=True)

        for nome_cli, dados in clientes_ordenados:
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**👤 {nome_cli}**")
                c2.write(f"📱 {dados['telefone'] if dados['telefone'] else 'N/A'}")
                c3.write(f"📦 Pedidos: **{dados['qtd_pedidos']}**")
                c4.markdown(f"💰 Total Comprado: **R$ {dados['total_gasto']:.2f}**")
                st.divider()
    else:
        st.info("Nenhuma venda realizada ainda para gerar o relatório de clientes.")

# ------------------------------------------
# ABA 3: HISTÓRICO & EDIÇÃO DE VALORES
# ------------------------------------------
with aba3:
    st.markdown("### 📜 Histórico de Vendas (Edição de Registros)")
    
    if historico_vendas:
        for idx, item in enumerate(historico_vendas):
            with st.expander(f"🗓️ {item['data_hora']} - {item['cliente']} | R$ {item['valor_final']:.2f}"):
                with st.form(key=f"form_edit_{item['id']}"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_cliente = st.text_input("Cliente", value=item['cliente'])
                        edit_tel = st.text_input("Telefone", value=item.get('telefone', ''))
                        edit_obs = st.text_input("Obs", value=item.get('observacao', ''))
                    
                    with col_e2:
                        edit_frango = st.number_input("Frangos", value=item['qtd_frango'], min_value=0)
                        edit_farofa = st.number_input("Farofas", value=item['qtd_farofa'], min_value=0)
                        edit_valor = st.number_input("💰 Valor Cobrado (Editável)", value=float(item['valor_final']), step=1.0)

                    c_salvar, _ = st.columns(2)
                    with c_salvar:
                        if st.form_submit_button("💾 Salvar Alterações"):
                            historico_vendas[idx]['cliente'] = edit_cliente
                            historico_vendas[idx]['telefone'] = edit_tel
                            historico_vendas[idx]['observacao'] = edit_obs
                            historico_vendas[idx]['qtd_frango'] = edit_frango
                            historico_vendas[idx]['qtd_farofa'] = edit_farofa
                            historico_vendas[idx]['valor_final'] = round(edit_valor, 2)
                            
                            salvar_historico(historico_vendas)
                            st.success("Registro atualizado com sucesso!")
                            st.rerun()

                if st.button("❌ Excluir Venda", key=f"del_{item['id']}"):
                    historico_vendas.pop(idx)
                    salvar_historico(historico_vendas)
                    st.rerun()
    else:
        st.info("Nenhum registro de venda encontrado.")

# ------------------------------------------
# ABA 4: TABELA DE PREÇOS PADRÃO
# ------------------------------------------
with aba4:
    st.markdown("### ⚙️ Preços Base dos Produtos")
    
    p_frango = st.number_input("Preço Frango Assado (R$)", value=float(precos_atuais['PRECO_FRANGO']))
    p_farofa = st.number_input("Preço Porção Farofa (R$)", value=float(precos_atuais['PRECO_FAROFA']))
    p_batata = st.number_input("Preço Batata Extra (R$)", value=float(precos_atuais['PRECO_BATATA_EXTRA']))
    p_refri = st.number_input("Preço Refrigerante (R$)", value=float(precos_atuais['PRECO_REFRIGERANTE']))

    if st.button("💾 Salvar Tabela de Preços", use_container_width=True):
        novos_precos = {
            'PRECO_FRANGO': p_frango,
            'PRECO_FAROFA': p_farofa,
            'PRECO_BATATA_EXTRA': p_batata,
            'PRECO_REFRIGERANTE': p_refri
        }
        local_storage.setItem("mv_precos", json.dumps(novos_precos))
        st.success("Tabela de preços salva!")
        st.rerun()