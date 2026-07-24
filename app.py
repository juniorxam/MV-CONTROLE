import streamlit as st
import json
from datetime import datetime
import pandas as pd
import urllib.parse
from streamlit_local_storage import LocalStorage
import io

# Bibliotecas para geração de PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuração da página Web
st.set_page_config(page_title="Frango Assado MV - Gestão Completa", page_icon="🍗", layout="wide")

# Inicializa LocalStorage
local_storage = LocalStorage()

# Configurações Padrões de Preços e Regras
CONFIG_PADRAO = {
    'PRECO_FRANGO': 60.00,       # Frango Assado (com batata inclusa)
    'PRECO_FAROFA': 5.00,        # Porção de Farofinha
    'PRECO_BATATA_EXTRA': 10.00, # Batata Extra
    'PRECO_REFRIGERANTE': 8.00,  # Refri 2L
    'META_FIDELIDADE': 10,       # Frangos para ganhar 1
    'ESTOQUE_INICIAL': 40        # Frangos colocados na churrasqueira no dia
}

# DADOS DE EXEMPLO SIMULADOS PARA UM DOMINGO (ATUALIZADO)
DADOS_EXEMPLO = [
    {
        'id': 1700000001,
        'data_hora': datetime.now().strftime("%d/%m/%Y") + " 10:45",
        'cliente': "Marko Pollo",
        'telefone': "63992543227",
        'tipo_pedido': "Retirada no Local",
        'horario_retirada': "11:00",
        'taxa_entrega': 0.0,
        'qtd_frango': 2,
        'qtd_farofa': 2,
        'qtd_batata': 1,
        'qtd_refri': 1,
        'subtotal': 148.00,
        'valor_final': 140.00,
        'forma_pagamento': "PIX",
        'observacao': "Desconto combo 2 frangos"
    },
    {
        'id': 1700000002,
        'data_hora': datetime.now().strftime("%d/%m/%Y") + " 11:10",
        'cliente': "Dona Maria (Matilde)",
        'telefone': "63984003344",
        'tipo_pedido': "Entrega (Delivery)",
        'horario_retirada': "11:30",
        'taxa_entrega': 5.0,
        'qtd_frango': 1,
        'qtd_farofa': 1,
        'qtd_batata': 0,
        'qtd_refri': 1,
        'subtotal': 78.00,
        'valor_final': 78.00,
        'forma_pagamento': "Dinheiro",
        'observacao': "Entregar na alameda 2, casa 15"
    },
    {
        'id': 1700000003,
        'data_hora': datetime.now().strftime("%d/%m/%Y") + " 11:30",
        'cliente': "João Paulo",
        'telefone': "63999112233",
        'tipo_pedido': "Retirada no Local",
        'horario_retirada': "12:00",
        'taxa_entrega': 0.0,
        'qtd_frango': 1,
        'qtd_farofa': 1,
        'qtd_batata': 0,
        'qtd_refri': 0,
        'subtotal': 65.00,
        'valor_final': 65.00,
        'forma_pagamento': "Cartão de Débito",
        'observacao': ""
    },
    {
        'id': 1700000004,
        'data_hora': datetime.now().strftime("%d/%m/%Y") + " 11:45",
        'cliente': "Marko Pollo",
        'telefone': "63992543227",
        'tipo_pedido': "Retirada no Local",
        'horario_retirada': "12:00",
        'taxa_entrega': 0.0,
        'qtd_frango': 8,
        'qtd_farofa': 4,
        'qtd_batata': 2,
        'qtd_refri': 2,
        'subtotal': 536.00,
        'valor_final': 500.00,
        'forma_pagamento': "PIX",
        'observacao': "Almoço de família - Atingiu Fidelidade!"
    }
]

# ==========================================
# FUNÇÕES DE SUPORTE
# ==========================================
def carregar_configuracoes():
    cfgs = local_storage.getItem("mv_precos")
    if cfgs:
        try:
            dados = json.loads(cfgs)
            res = CONFIG_PADRAO.copy()
            res.update(dados)
            return res
        except:
            return CONFIG_PADRAO.copy()
    return CONFIG_PADRAO.copy()

def carregar_historico():
    hist = local_storage.getItem("mv_historico")
    if hist is None:
        local_storage.setItem("mv_historico", json.dumps(DADOS_EXEMPLO))
        return DADOS_EXEMPLO
    try:
        return json.loads(hist)
    except:
        return []

def salvar_historico(historico):
    local_storage.setItem("mv_historico", json.dumps(historico))

def gerar_link_whatsapp(venda):
    tel = "".join([c for c in str(venda.get('telefone', '')) if c.isdigit()])
    if not tel:
        return None
    
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
        
    msg += f"\n⏰ *Horário Previsto:* {venda.get('horario_retirada', 'Imediato')}\n"
    msg += f"🛵 *Tipo:* {venda.get('tipo_pedido', 'Retirada')}\n"
    msg += f"💳 *Pagamento:* {venda.get('forma_pagamento', 'Não Informado')}\n"
    msg += f"💰 *TOTAL:* R$ {venda['valor_final']:.2f}\n"
    
    if venda.get('observacao'):
        msg += f"📝 *Obs:* {venda['observacao']}\n"
        
    msg += "\nObrigado pela preferência e bom apetite! ❤️"
    
    texto_encoded = urllib.parse.quote(msg)
    return f"https://wa.me/{tel}?text={texto_encoded}"

def gerar_cupom_texto(venda):
    cupom = f"================================\n"
    cupom += f"       FRANGO ASSADO MV\n"
    cupom += f"   Sabor que Conquista - 407 Norte\n"
    cupom += f"================================\n"
    cupom += f"Data/Hora: {venda['data_hora']}\n"
    cupom += f"Cliente  : {venda['cliente']}\n"
    cupom += f"Telefone : {venda.get('telefone', 'N/A')}\n"
    cupom += f"Tipo     : {venda.get('tipo_pedido', 'Retirada')}\n"
    cupom += f"Horário  : {venda.get('horario_retirada', 'Imediato')}\n"
    cupom += f"--------------------------------\n"
    if venda['qtd_frango'] > 0: cupom += f"{venda['qtd_frango']}x Frango Assado c/ Batata\n"
    if venda['qtd_farofa'] > 0: cupom += f"{venda['qtd_farofa']}x Porcao de Farofa\n"
    if venda['qtd_batata'] > 0: cupom += f"{venda['qtd_batata']}x Batata Extra\n"
    if venda['qtd_refri'] > 0:  cupom += f"{venda['qtd_refri']}x Refrigerante\n"
    if venda.get('taxa_entrega', 0) > 0: cupom += f"Taxa de Entrega: R$ {venda['taxa_entrega']:.2f}\n"
    cupom += f"--------------------------------\n"
    cupom += f"Pagamento : {venda.get('forma_pagamento', 'N/A')}\n"
    cupom += f"TOTAL     : R$ {venda['valor_final']:.2f}\n"
    if venda.get('observacao'):
        cupom += f"Obs: {venda['observacao']}\n"
    cupom += f"================================\n"
    return cupom

def gerar_pdf_relatorio(df_dia, data_str):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    # Título do Relatório
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1, textColor=colors.HexColor("#D35400"))
    story.append(Paragraph("<b>FRANGO ASSADO MV - RELATÓRIO DE VENDAS</b>", title_style))
    
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=11, alignment=1)
    story.append(Paragraph(f"Data do Relatório: {data_str} | 407 Norte - Palmas/TO", sub_style))
    story.append(Spacer(1, 15))

    # Métricas Gerais
    total_fat = df_dia['valor_final'].sum()
    total_frangos = df_dia['qtd_frango'].sum()
    total_pedidos = len(df_dia)
    
    m_data = [
        ["Faturamento Total", "Frangos Vendidos", "Qtd. Pedidos"],
        [f"R$ {total_fat:.2f}", f"{total_frangos} un.", f"{total_pedidos}"]
    ]
    t_m = Table(m_data, colWidths=[180, 180, 180])
    t_m.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F39C12")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor("#FCF3CF")),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#D35400")),
    ]))
    story.append(t_m)
    story.append(Spacer(1, 15))

    # Tabela de Pedidos
    story.append(Paragraph("<b>Detalhamento das Vendas:</b>", styles['Heading2']))
    story.append(Spacer(1, 5))

    table_data = [["Hora", "Cliente", "Itens", "Horário", "Pagamento", "Total"]]
    for _, row in df_dia.iterrows():
        itens = f"{row['qtd_frango']} Frango(s)"
        if row['qtd_farofa'] > 0: itens += f", {row['qtd_farofa']} Farofa(s)"
        
        table_data.append([
            row['data_hora'].split(" ")[1] if " " in row['data_hora'] else "",
            str(row['cliente'])[:18],
            itens,
            str(row.get('horario_retirada', 'Imediato')),
            str(row.get('forma_pagamento', '')),
            f"R$ {row['valor_final']:.2f}"
        ])

    t_pedidos = Table(table_data, colWidths=[45, 120, 150, 65, 85, 75])
    t_pedidos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (-1,0), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F2F4F4")])
    ]))
    story.append(t_pedidos)

    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# INTERFACE GRÁFICA
# ==========================================
st.title("🍗 Frango Assado MV")

configs_atuais = carregar_configuracoes()
historico_vendas = carregar_historico()

# BARRA DE FERRAMENTAS DO TOPO
col_top1, col_top2 = st.columns([3, 1])
with col_top1:
    st.caption("📍 Endereço: 407 Norte (Em frente ao Supermercado da Matilde) | 📞 (63) 99297-1557")
with col_top2:
    if st.button("🗑️ ZERAR DADOS PARA INICIAR VENDAS", type="secondary", use_container_width=True):
        salvar_historico([])
        st.success("Histórico limpo!")
        st.rerun()

# CÁLCULO DE ESTOQUE EM TEMPO REAL
hoje_str = datetime.now().strftime("%d/%m/%Y")
frangos_vendidos_hoje = sum(
    v.get('qtd_frango', 0) for v in historico_vendas 
    if v.get('data_hora', '').startswith(hoje_str)
)
estoque_maximo = int(configs_atuais.get('ESTOQUE_INICIAL', 40))
estoque_restante = max(0, estoque_maximo - frangos_vendidos_hoje)

col_est1, col_est2, col_est3 = st.columns(3)
col_est1.metric("🔥 Frangos Assando (Dia)", f"{estoque_maximo} un.")
col_est2.metric("✅ Frangos Vendidos Hoje", f"{frangos_vendidos_hoje} un.")
col_est3.metric("🚨 Restantes na Churrasqueira", f"{estoque_restante} un.", 
                delta=f"-{frangos_vendidos_hoje}" if frangos_vendidos_hoje > 0 else "Total", 
                delta_color="inverse")

st.markdown("---")

aba_dash, aba_grelha, aba1, aba2, aba3, aba4, aba_ajuda = st.tabs([
    "📊 Dashboard & PDF", 
    "🔥 Grelha & Reservas",
    "🛒 Nova Venda", 
    "👥 Clientes & Fidelidade", 
    "📜 Histórico & Edição", 
    "⚙️ Configurações",
    "📖 Manual & Dicas"
])

# ------------------------------------------
# ABA DASHBOARD & RELATÓRIO PDF
# ------------------------------------------
with aba_dash:
    st.markdown("### 📊 Painel de Vendas e Relatório em PDF")
    
    if historico_vendas:
        df = pd.DataFrame(historico_vendas)
        df['data_dt'] = pd.to_datetime(df['data_hora'], format="%d/%m/%Y %H:%M")
        df['data_str'] = df['data_dt'].dt.strftime("%d/%m/%Y")
        
        datas_disponiveis = df['data_str'].unique()
        
        col_filtro, col_pdf_btn = st.columns([2, 2])
        with col_filtro:
            data_selecionada = st.selectbox("🗓️ Selecione o Domingo/Dia:", datas_disponiveis, index=0)
        
        df_dia = df[df['data_str'] == data_selecionada]
        
        with col_pdf_btn:
            st.write(" ") # Espaçamento
            pdf_bytes = gerar_pdf_relatorio(df_dia, data_selecionada)
            st.download_button(
                label="📄 BAIXAR RELATÓRIO DE VENDAS EM PDF",
                data=pdf_bytes,
                file_name=f"relatorio_vendas_{data_selecionada.replace('/', '_')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

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
        
        st.markdown("#### 💵 Fechamento de Caixa do Dia (Conferência)")
        pix_total = df_dia[df_dia['forma_pagamento'] == 'PIX']['valor_final'].sum()
        dinheiro_total = df_dia[df_dia['forma_pagamento'] == 'Dinheiro']['valor_final'].sum()
        credito_total = df_dia[df_dia['forma_pagamento'] == 'Cartão de Crédito']['valor_final'].sum()
        debito_total = df_dia[df_dia['forma_pagamento'] == 'Cartão de Débito']['valor_final'].sum()
        
        c_cx1, c_cx2, c_cx3, c_cx4 = st.columns(4)
        c_cx1.metric("📲 Total no PIX", f"R$ {pix_total:.2f}")
        c_cx2.metric("💵 Dinheiro na Gaveta", f"R$ {dinheiro_total:.2f}")
        c_cx3.metric("💳 Cartão de Crédito", f"R$ {credito_total:.2f}")
        c_cx4.metric("💳 Cartão de Débito", f"R$ {debito_total:.2f}")
        
        st.markdown("---")
        
        c_graf1, c_graf2 = st.columns(2)
        with c_graf1:
            st.markdown("#### 💳 Forma de Pagamento")
            df_pag = df_dia.groupby('forma_pagamento')['valor_final'].sum().reset_index()
            st.bar_chart(data=df_pag, x='forma_pagamento', y='valor_final', height=200)
            
        with c_graf2:
            st.markdown("#### 📈 Histórico por Domingo")
            df_agrupado_dia = df.groupby('data_str', as_index=False)['valor_final'].sum()
            st.bar_chart(data=df_agrupado_dia, x='data_str', y='valor_final', height=200)
    else:
        st.info("Nenhuma venda registrada ainda para exibir dados no Dashboard.")

# ------------------------------------------
# ABA GRELHA & RESERVAS POR HORÁRIO
# ------------------------------------------
with aba_grelha:
    st.markdown("### 🔥 Controle de Grelha e Fila de Retiradas")
    
    if historico_vendas:
        df_grelha = pd.DataFrame(historico_vendas)
        df_grelha['data_str'] = pd.to_datetime(df_grelha['data_hora'], format="%d/%m/%Y %H:%M").dt.strftime("%d/%m/%Y")
        
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        df_hoje = df_grelha[df_grelha['data_str'] == data_hoje]
        
        if not df_hoje.empty:
            horarios = df_hoje['horario_retirada'].unique()
            horarios_ordenados = sorted(horarios)
            
            for h in horarios_ordenados:
                pedidos_horario = df_hoje[df_hoje['horario_retirada'] == h]
                qtd_frangos_horario = pedidos_horario['qtd_frango'].sum()
                
                with st.expander(f"⏰ Horário {h} — {len(pedidos_horario)} pedido(s) | 🍗 {qtd_frangos_horario} frango(s) a preparar", expanded=True):
                    for _, ped in pedidos_horario.iterrows():
                        col_p1, col_p2, col_p3, col_p4 = st.columns([3, 2, 2, 2])
                        col_p1.write(f"👤 **{ped['cliente']}** ({ped['tipo_pedido']})")
                        col_p2.write(f"🍗 {ped['qtd_frango']} Frangos | 🥣 {ped['qtd_farofa']} Farofas")
                        col_p3.write(f"💰 R$ {ped['valor_final']:.2f} ({ped['forma_pagamento']})")
                        
                        link_wsp = gerar_link_whatsapp(ped.to_dict())
                        if link_wsp:
                            col_p4.markdown(f"[📲 WhatsApp]({link_wsp})")
                        else:
                            col_p4.caption("Sem Tel")
                        
                        if ped.get('observacao'):
                            st.caption(f"📌 Obs: {ped['observacao']}")
                        st.divider()
        else:
            st.info("Nenhum pedido registrado para o dia de hoje.")
    else:
        st.info("Nenhum pedido cadastrado no sistema.")

# ------------------------------------------
# ABA 1: NOVA VENDA
# ------------------------------------------
with aba1:
    st.markdown("### 📝 Registrar Novo Pedido")
    
    col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
    with col_c1:
        cliente_nome = st.text_input("Nome do Cliente", placeholder="Ex: Marko Pollo")
    with col_c2:
        telefone = st.text_input("WhatsApp (DDD+Número)", placeholder="63992543227")
    with col_c3:
        tipo_pedido = st.selectbox("Tipo de Pedido", ["Retirada no Local", "Entrega (Delivery)"])

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        horario_retirada = st.selectbox("⏰ Horário de Retirada / Entrega", [
            "Imediato / Balcão", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30"
        ])
    with col_h2:
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
        (qtd_frango * configs_atuais['PRECO_FRANGO']) +
        (qtd_farofa * configs_atuais['PRECO_FAROFA']) +
        (qtd_batata * configs_atuais['PRECO_BATATA_EXTRA']) +
        (qtd_refri * configs_atuais['PRECO_REFRIGERANTE']) +
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
            'horario_retirada': horario_retirada,
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
        
        st.session_state['ultima_venda'] = nova_venda
        st.success(f"Venda registrada com sucesso! Total: R$ {valor_final:.2f}")
        st.rerun()

    if 'ultima_venda' in st.session_state:
        uv = st.session_state['ultima_venda']
        st.markdown("---")
        st.markdown("#### 📄 Ações da Última Venda Registrada")
        
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            link_zap = gerar_link_whatsapp(uv)
            if link_zap:
                st.markdown(f"👉 [📲 **Clique Aqui para Enviar a Mensagem no WhatsApp do Cliente**]({link_zap})")
            else:
                st.info("Número de WhatsApp não informado no cadastro deste pedido.")
        
        with col_act2:
            cupom_txt = gerar_cupom_texto(uv)
            st.download_button(
                label="🖨️ Baixar Cupom do Pedido (Imprimir)",
                data=cupom_txt,
                file_name=f"cupom_{uv['cliente'].replace(' ', '_')}.txt",
                mime="text/plain"
            )

# ------------------------------------------
# ABA 2: CLIENTES & FIDELIDADE
# ------------------------------------------
with aba2:
    st.markdown("### 👥 Ranking de Clientes e Cartão Fidelidade")
    meta = configs_atuais.get('META_FIDELIDADE', 10)
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
                
                st.progress(progresso, text=f"Fidelidade: {frangos_acumulados}/{meta} frangos comprados")
                if frangos_acumulados >= meta:
                    st.success("🎉 Este cliente atingiu a meta para ganhar um brinde/desconto!")
                st.divider()
    else:
        st.info("Nenhuma venda realizada ainda para gerar a lista de clientes.")

# ------------------------------------------
# ABA 3: HISTÓRICO & EDIÇÃO DE VALORES
# ------------------------------------------
with aba3:
    st.markdown("### 📜 Histórico de Vendas (Envio WhatsApp e Edição)")
    
    if historico_vendas:
        for idx, item in enumerate(historico_vendas):
            with st.expander(f"🗓️ {item['data_hora']} - {item['cliente']} | R$ {item['valor_final']:.2f} ({item.get('forma_pagamento', 'N/I')})"):
                
                # BOTÃO DIRETO DE WHATSAPP NO HISTÓRICO
                link_zap_hist = gerar_link_whatsapp(item)
                if link_zap_hist:
                    st.markdown(f"📲 [**Enviar/Reenviar Comprovante no WhatsApp do Cliente**]({link_zap_hist})")
                else:
                    st.caption("⚠️ Nenhum telefone cadastrado para este pedido.")
                
                st.markdown("---")
                
                with st.form(key=f"form_edit_{item['id']}"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_cliente = st.text_input("Cliente", value=item['cliente'])
                        edit_tel = st.text_input("Telefone", value=item.get('telefone', ''))
                        edit_pag = st.selectbox("Forma Pagamento", ["PIX", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"], index=["PIX", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"].index(item.get('forma_pagamento', 'PIX')))
                        edit_horario = st.selectbox("Horário Retirada", ["Imediato / Balcão", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30"], index=0)
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
                            historico_vendas[idx]['horario_retirada'] = edit_horario
                            historico_vendas[idx]['observacao'] = edit_obs
                            historico_vendas[idx]['qtd_frango'] = edit_frango
                            historico_vendas[idx]['qtd_farofa'] = edit_farofa
                            historico_vendas[idx]['valor_final'] = round(edit_valor, 2)
                            
                            salvar_historico(historico_vendas)
                            st.success("Registro atualizado com sucesso!")
                            st.rerun()

                cupom_hist = gerar_cupom_texto(item)
                st.download_button(
                    label="🖨️ Baixar Cupom do Pedido",
                    data=cupom_hist,
                    file_name=f"cupom_{item['id']}.txt",
                    mime="text/plain",
                    key=f"btn_cp_{item['id']}"
                )

                if st.button("❌ Excluir Venda", key=f"del_{item['id']}"):
                    historico_vendas.pop(idx)
                    salvar_historico(historico_vendas)
                    st.rerun()
    else:
        st.info("Nenhum registro de venda encontrado.")

# ------------------------------------------
# ABA 4: CONFIGURAÇÕES DE PREÇOS E ESTOQUE
# ------------------------------------------
with aba4:
    st.markdown("### ⚙️ Configurações de Preços, Estoque e Fidelidade")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_frango = st.number_input("Preço Frango Assado (R$)", value=float(configs_atuais['PRECO_FRANGO']))
        p_farofa = st.number_input("Preço Porção Farofa (R$)", value=float(configs_atuais['PRECO_FAROFA']))
        est_dia = st.number_input("🔥 Estoque Inicial de Frangos no Dia (Grelha)", value=int(configs_atuais.get('ESTOQUE_INICIAL', 40)), step=5)
    with col_p2:
        p_batata = st.number_input("Preço Batata Extra (R$)", value=float(configs_atuais['PRECO_BATATA_EXTRA']))
        p_refri = st.number_input("Preço Refrigerante (R$)", value=float(configs_atuais['PRECO_REFRIGERANTE']))
        meta_fid = st.number_input("Meta de Frangos para Cartão Fidelidade", value=int(configs_atuais.get('META_FIDELIDADE', 10)), step=1)

    if st.button("💾 Salvar Configurações", use_container_width=True):
        novas_cfgs = {
            'PRECO_FRANGO': p_frango,
            'PRECO_FAROFA': p_farofa,
            'PRECO_BATATA_EXTRA': p_batata,
            'PRECO_REFRIGERANTE': p_refri,
            'META_FIDELIDADE': meta_fid,
            'ESTOQUE_INICIAL': est_dia
        }
        local_storage.setItem("mv_precos", json.dumps(novas_cfgs))
        st.success("Configurações salvas!")
        st.rerun()

# ------------------------------------------
# ABA 5: MANUAL E ORIENTAÇÕES DE USO
# ------------------------------------------
with aba_ajuda:
    st.markdown("### 📖 Guia de Uso — Frango Assado MV")
    
    st.markdown("""
    Bem-vindo ao sistema de gestão do **Frango Assado MV**!
    
    ---
    
    #### 📲 Como mandar mensagem por WhatsApp?
    1. **Logo após cadastrar:** Na aba `🛒 Nova Venda`, logo que você salva um pedido, aparece um botão verde **"Clique Aqui para Enviar a Mensagem no WhatsApp do Cliente"**.
    2. **A qualquer momento:** Na aba `📜 Histórico & Edição` ou na aba `🔥 Grelha & Reservas`, você verá um link de WhatsApp em **cada pedido individual**. É só clicar que abre a conversa no celular ou PC com o resumo formatado!
    
    #### 📄 Como baixar o Relatório em PDF?
    * Acesse a aba **`📊 Dashboard & PDF`**.
    * Selecione a data do domingo desejado.
    * Clique no botão azul **`📄 BAIXAR RELATÓRIO DE VENDAS EM PDF`**.
    """)
