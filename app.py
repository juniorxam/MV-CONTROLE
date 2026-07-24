import streamlit as st
import json
from datetime import datetime
import pandas as pd
import urllib.parse
from streamlit_local_storage import LocalStorage

# Configuração da página Web
st.set_page_config(page_title="Frango Assado MV - Gestão Completa", page_icon="🍗", layout="wide")

# Inicializa LocalStorage
local_storage = LocalStorage()

# Configurações Padrões de Preços (R$)
PRECOS_PADRAO = {
    'PRECO_FRANGO': 60.00,       # Frango Assado (com batata inclusa)
    'PRECO_FAROFA': 5.00,        # Porção de Farofinha
    'PRECO_BATATA_EXTRA': 10.00, # Batata Extra
    'PRECO_REFRIGERANTE': 8.00,  # Refri 2L
    'META_FIDELIDADE': 10        # Frangos comprados para ganhar 1
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

def gerar_link_whatsapp(venda):
    tel = "".join([c for c in str(venda.get('telefone', '')) if c.isdigit()])
    if not tel:
        return None
    
    # Ajusta DDI do Brasil se não estiver presente
    if len(tel) <= 11 and not tel.startswith("55"):
        tel = "55" + tel

    msg = f"Olá, *{venda['cliente']}*! 👋\n"
    msg += f"Seu pedido no *Frango Assado MV* foi registrado! 🍗\n\n"
    msg += f"📋 *Resumo do Pedido:*\n"
    if venda['qtd_frango'] > 0: msg += f"• {venda['qtd_frango']}x Frango Assado\n"
    if venda['qtd_farofa'] > 0: msg += f"• {venda['qtd_farofa']}x Porção de Farofa\n"
    if venda['qtd_batata'] > 0: msg += f"• {venda['qtd_batata']}x Batata Extra\n"
    if venda['qtd_refri'] > 0: msg += f"• {venda['qtd_refri']}x Refrigerante\n"
    
    if venda.get('taxa_entrega', 0) > 0:
        msg += f"• Taxa de Entrega: R$ {venda['taxa_entrega']:.2f}\n"
        
    msg += f"\n🛵 *Tipo:* {venda.get('tipo_pedido', 'Retirada')}\n"
    msg += f"💳 *Pagamento:* {venda.get('forma_pagamento', 'Não Informado')}\n"
    msg += f"💰 *TOTAL:* R$ {venda['valor_final']:.2f}\n"
    
    if venda.get('observacao'):
        msg += f"📝 *Obs:* {venda['observacao']}\n"
        
    msg += "\nObrigado pela preferência e bom apetite! ❤️"
    
    texto_encoded = urllib.parse.quote(msg)
    return f"https://wa.me/{tel}?text={texto_encoded}"

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
    "👥 Clientes & Fidelidade", 
    "📜 Histórico & Edição", 
    "⚙️ Configurações"
])

# ------------------------------------------
# ABA DASHBOARD: PAINEL DE DESEMPENHO
# ------------------------------------------
with aba_dash:
    st.markdown("### 📊 Painel de Vendas")
    
    if historico_vendas:
        df = pd.DataFrame(historico_vendas)
        
        # Tratamento das datas
        df['data_dt'] = pd.to_datetime(df['data_hora'], format="%d/%m/%Y %H:%M")
        df['data_str'] = df['data_dt'].dt.strftime("%d/%m/%Y")
        
        datas_disponiveis = df['data_str'].unique()
        
        col_filtro, _ = st.columns([2, 2])
        with col_filtro:
            data_selecionada = st.selectbox("🗓️ Selecione o Domingo/Dia:", datas_disponiveis, index=0)
        
        df_dia = df[df['data_str'] == data_selecionada]
        
        total_faturado_dia = df_dia['valor_final'].sum()
        total_frangos_dia = df_dia['qtd_frango'].sum()
        total_pedidos_dia = len(df_dia)
        ticket_medio = total_faturado_dia / total_pedidos_dia if total_pedidos_dia > 0 else 0
        
        st.markdown(f"#### 🎯 Resumo de {data_selecionada}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Faturamento Total", f"R$ {total_faturado_dia:.2f}")
        m2.metric("🍗 Frangos Vendidos", f"{total_frangos_dia} un.")
        m3.metric("📦 Pedidos Atendidos", f"{total_pedidos_dia}")
        m4.metric("🏷️ Ticket Médio", f"R$ {ticket_medio:.2f}")
        
        st.markdown("---")
        
        c_graf1, c_graf2 = st.columns(2)
        with c_graf1:
            st.markdown("#### 💳 Vendas por Pagamento (Dia)")
            df_pag = df_dia.groupby('forma_pagamento')['valor_final'].sum().reset_index()
            st.bar_chart(data=df_pag, x='forma_pagamento', y='valor_final', height=200)
            
        with c_graf2:
            st.markdown("#### 📈 Faturamento por Domingo")
            df_agrupado_dia = df.groupby('data_str', as_index=False)['valor_final'].sum()
            st.bar_chart(data=df_agrupado_dia, x='data_str', y='valor_final', height=200)

        # Botão de Exportar CSV
        st.markdown("---")
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Todas as Vendas em Excel/CSV",
            data=csv_data,
            file_name=f"vendas_frango_mv_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhuma venda registrada ainda para exibir dados no Dashboard.")

# ------------------------------------------
# ABA 1: NOVA VENDA (MELHORADA)
# ------------------------------------------
with aba1:
    st.markdown("### 📝 Registrar Novo Pedido")
    
    col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
    with col_c1:
        cliente_nome = st.text_input("Nome do Cliente", placeholder="Ex: João da 407 Norte")
    with col_c2:
        telefone = st.text_input("WhatsApp (DDD+Número)", placeholder="63992971557")
    with col_c3:
        tipo_pedido = st.selectbox("Tipo de Pedido", ["Retirada no Local", "Entrega (Delivery)"])

    taxa_entrega = 0.0
    if tipo_pedido == "Entrega (Delivery)":
        taxa_entrega = st.number_input("Taxa de Entrega (R$)", min_value=0.0, value=5.0, step=1.0)

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

    subtotal = (
        (qtd_frango * precos_atuais['PRECO_FRANGO']) +
        (qtd_farofa * precos_atuais['PRECO_FAROFA']) +
        (qtd_batata * precos_atuais['PRECO_BATATA_EXTRA']) +
        (qtd_refri * precos_atuais['PRECO_REFRIGERANTE']) +
        taxa_entrega
    )

    st.markdown("---")
    st.markdown("#### Pagamento e Valor Final")
    
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        st.metric("Subtotal Calculado", f"R$ {subtotal:.2f}")
    with col_v2:
        valor_final = st.number_input("💰 Valor Final Cobrado (Com Desconto/Ajuste)", min_value=0.0, value=float(subtotal), step=1.0, format="%.2f")
    with col_v3:
        forma_pagamento = st.selectbox("Forma de Pagamento", ["PIX", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"])

    valor_recebido = 0.0
    if forma_pagamento == "Dinheiro":
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            valor_recebido = st.number_input("Valor Recebido em Dinheiro (R$)", min_value=0.0, value=float(valor_final), step=5.0)
        with col_t2:
            troco = max(0.0, valor_recebido - valor_final)
            st.metric("💵 Troco a Devolver", f"R$ {troco:.2f}")

    obs = st.text_input("Observações do Pedido / Endereço de Entrega", placeholder="Ex: Entregar perto do mercado / Sem pimenta")

    if st.button("✅ Confirmar e Finalizar Venda", type="primary", use_container_width=True):
        nova_venda = {
            'id': int(datetime.now().timestamp()),
            'data_hora': datetime.now().strftime("%d/%m/%Y %H:%M"),
            'cliente': cliente_nome.strip() if cliente_nome.strip() else "Cliente Não Identificado",
            'telefone': telefone.strip(),
            'tipo_pedido': tipo_pedido,
            'taxa_entrega': taxa_entrega,
            'qtd_frango': qtd_frango,
            'qtd_farofa': qtd_farofa,
            'qtd_batata': qtd_batata,
            'qtd_refri': qtd_refri,
            'subtotal': round(subtotal, 2),
            'valor_final': round(valor_final, 2),
            'forma_pagamento': forma_pagamento,
            'observacao': obs
        }
        
        historico_vendas.insert(0, nova_venda)
        salvar_historico(historico_vendas)
        
        link_zap = gerar_link_whatsapp(nova_venda)
        st.success(f"Venda registrada com sucesso! Total: R$ {valor_final:.2f}")
        
        if link_zap:
            st.markdown(f"[📲 **Clique aqui para enviar o Comprovante no WhatsApp do Cliente**]({link_zap})")
            
        st.rerun()

# ------------------------------------------
# ABA 2: CLIENTES & FIDELIDADE
# ------------------------------------------
with aba2:
    st.markdown("### 👥 Ranking de Clientes e Cartão Fidelidade")
    meta = precos_atuais.get('META_FIDELIDADE', 10)
    st.caption(f"Meta do Programa Fidelidade: A cada **{meta} frangos assados**, o cliente pode ganhar um brinde!")
    
    if historico_vendas:
        resumo_clientes = {}
        for v in historico_vendas:
            nome = v['cliente']
            val = v['valor_final']
            frangos = v.get('qtd_frango', 0)
            
            if nome in resumo_clientes:
                resumo_clientes[nome]['total_gasto'] += val
                resumo_clientes[nome]['total_frangos'] += frangos
                resumo_clientes[nome]['qtd_pedidos'] += 1
                if v['telefone'] and not resumo_clientes[nome]['telefone']:
                    resumo_clientes[nome]['telefone'] = v['telefone']
            else:
                resumo_clientes[nome] = {
                    'total_gasto': val,
                    'total_frangos': frangos,
                    'qtd_pedidos': 1,
                    'telefone': v.get('telefone', '')
                }

        clientes_ordenados = sorted(resumo_clientes.items(), key=lambda x: x[1]['total_gasto'], reverse=True)

        for nome_cli, dados in clientes_ordenados:
            frangos_acumulados = dados['total_frangos']
            progresso = min(1.0, frangos_acumulados / meta)
            
            with st.container():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                c1.markdown(f"**👤 {nome_cli}**")
                c2.write(f"📱 {dados['telefone'] if dados['telefone'] else 'N/A'}")
                c3.write(f"📦 Pedidos: **{dados['qtd_pedidos']}** | 🍗 Frangos: **{frangos_acumulados}**")
                c4.markdown(f"💰 Total Gasto: **R$ {dados['total_gasto']:.2f}**")
                
                # Progresso Fidelidade
                st.progress(progresso, text=f"Fidelidade: {frangos_acumulados}/{meta} frangos comprados")
                if frangos_acumulados >= meta:
                    st.balloons()
                    st.success("🎉 Este cliente atingiu a meta para ganhar um brinde/desconto!")
                st.divider()
    else:
        st.info("Nenhuma venda realizada ainda para gerar a lista de clientes.")

# ------------------------------------------
# ABA 3: HISTÓRICO & EDIÇÃO DE VALORES
# ------------------------------------------
with aba3:
    st.markdown("### 📜 Histórico de Vendas (Edição de Registros)")
    
    if historico_vendas:
        for idx, item in enumerate(historico_vendas):
            with st.expander(f"🗓️ {item['data_hora']} - {item['cliente']} | R$ {item['valor_final']:.2f} ({item.get('forma_pagamento', 'N/I')})"):
                with st.form(key=f"form_edit_{item['id']}"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_cliente = st.text_input("Cliente", value=item['cliente'])
                        edit_tel = st.text_input("Telefone", value=item.get('telefone', ''))
                        edit_pag = st.selectbox("Forma Pagamento", ["PIX", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"], index=["PIX", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"].index(item.get('forma_pagamento', 'PIX')))
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
                            historico_vendas[idx]['forma_pagamento'] = edit_pag
                            historico_vendas[idx]['observacao'] = edit_obs
                            historico_vendas[idx]['qtd_frango'] = edit_frango
                            historico_vendas[idx]['qtd_farofa'] = edit_farofa
                            historico_vendas[idx]['valor_final'] = round(edit_valor, 2)
                            
                            salvar_historico(historico_vendas)
                            st.success("Registro atualizado com sucesso!")
                            st.rerun()

                link_zap_hist = gerar_link_whatsapp(item)
                if link_zap_hist:
                    st.markdown(f"[📲 Reenviar Comprovante no WhatsApp]({link_zap_hist})")

                if st.button("❌ Excluir Venda", key=f"del_{item['id']}"):
                    historico_vendas.pop(idx)
                    salvar_historico(historico_vendas)
                    st.rerun()
    else:
        st.info("Nenhum registro de venda encontrado.")

# ------------------------------------------
# ABA 4: CONFIGURAÇÕES DE PREÇOS E FIDELIDADE
# ------------------------------------------
with aba4:
    st.markdown("### ⚙️ Preços Base e Regras")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_frango = st.number_input("Preço Frango Assado (R$)", value=float(precos_atuais['PRECO_FRANGO']))
        p_farofa = st.number_input("Preço Porção Farofa (R$)", value=float(precos_atuais['PRECO_FAROFA']))
    with col_p2:
        p_batata = st.number_input("Preço Batata Extra (R$)", value=float(precos_atuais['PRECO_BATATA_EXTRA']))
        p_refri = st.number_input("Preço Refrigerante (R$)", value=float(precos_atuais['PRECO_REFRIGERANTE']))
    
    meta_fid = st.number_input("Meta de Frangos para Cartão Fidelidade", value=int(precos_atuais.get('META_FIDELIDADE', 10)), step=1)

    if st.button("💾 Salvar Configurações", use_container_width=True):
        novos_precos = {
            'PRECO_FRANGO': p_frango,
            'PRECO_FAROFA': p_farofa,
            'PRECO_BATATA_EXTRA': p_batata,
            'PRECO_REFRIGERANTE': p_refri,
            'META_FIDELIDADE': meta_fid
        }
        local_storage.setItem("mv_precos", json.dumps(novos_precos))
        st.success("Configurações salvas!")
        st.rerun()
