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

# Biblioteca para geração de Imagem do Cupom
from PIL import Image, ImageDraw, ImageFont

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

# DADOS DE EXEMPLO SIMULADOS (MARKO POLLO COMO PRINCIPAL PARA TESTE)
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
        'valor_recebido': 140.00,
        'troco': 0.0,
        'forma_pagamento': "PIX",
        'observacao': "Pedido de teste - Marko Pollo"
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
        'valor_recebido': 100.00,
        'troco': 22.00,
        'forma_pagamento': "Dinheiro",
        'observacao': "Entregar na alameda 2, casa 15"
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

def gerar_link_whatsapp(venda, status="confirmado"):
    tel = "".join([c for c in str(venda.get('telefone', '')) if c.isdigit()])
    if not tel or len(tel) < 10:
        return None
    
    if len(tel) <= 11 and not tel.startswith("55"):
        tel = "55" + tel

    if status == "pronto":
        msg = f"🎉 *SEU PEDIDO ESTÁ PRONTO!* 🎉\n"
        msg += f"Olá, *{venda['cliente']}*! Seu frango assado quentinho já está na estufa te esperando! 🍗🔥\n\n"
        msg += f"📍 *Local de Retirada:* 407 Norte (Em frente ao Supermercado da Matilde)\n"
        msg += f"💰 *Valor Total:* R$ {venda['valor_final']:.2f} ({venda.get('forma_pagamento', 'N/A')})\n"
        msg += f"\nPode vir retirar! Estamos te aguardando. 😊"

    elif status == "entrega":
        msg = f"🛵 *PEDIDO SAIU PARA ENTREGA!* 🛵\n"
        msg += f"Olá, *{venda['cliente']}*! O entregador acabou de sair com o seu pedido! 🚀\n\n"
        msg += f"💰 *Total:* R$ {venda['valor_final']:.2f} ({venda.get('forma_pagamento', 'N/A')})\n"
        
        if venda.get('troco', 0) > 0:
            msg += f"💵 *Troco que o entregador está levando:* R$ {venda['troco']:.2f}\n"
            
        if venda.get('observacao'):
            msg += f"📌 *Endereço/Obs:* {venda['observacao']}\n"
            
        msg += f"\nChega já aí quentinho! Bom apetite! ❤️"

    else:  # Status Padrão: 'confirmado'
        msg = f"Olá, *{venda['cliente']}*! 👋\n"
        msg += f"Seu pedido no *Frango Assado MV* foi registrado com sucesso! 🍗\n\n"
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
        
        if venda.get('troco', 0) > 0:
            msg += f"💵 *Troco a Levar:* R$ {venda['troco']:.2f}\n"

        msg += f"💰 *TOTAL:* R$ {venda['valor_final']:.2f}\n"
        msg += "\nObrigado pela preferência! ❤️"
    
    texto_encoded = urllib.parse.quote(msg)
    return f"https://wa.me/{tel}?text={texto_encoded}"

def gerar_cupom_imagem(venda):
    """
    Gera uma imagem elegante no estilo recibo/cupom em formato PNG.
    """
    width = 500
    height = 680
    
    # Criar imagem com fundo creme claro (estilo papel de recibo)
    bg_color = (255, 253, 245)
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Tentar carregar fonte padrão do sistema
    try:
        font_title = ImageFont.truetype("arial.ttf", 22)
        font_subtitle = ImageFont.truetype("arial.ttf", 13)
        font_bold = ImageFont.truetype("arialbd.ttf", 15)
        font_text = ImageFont.truetype("arial.ttf", 14)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_title = font_subtitle = font_bold = font_text = font_small = ImageFont.load_default()

    # Cores
    c_orange = (211, 84, 0)
    c_dark = (44, 62, 80)
    c_gray = (127, 140, 141)

    # 1. Cabeçalho Laranja
    draw.rectangle([0, 0, width, 85], fill=c_orange)
    draw.text((width//2, 25), "🍗 FRANGO ASSADO MV", fill=(255, 255, 255), font=font_title, anchor="mm")
    draw.text((width//2, 58), "Sabor que Conquista • 407 Norte - Palmas/TO", fill=(255, 245, 230), font=font_subtitle, anchor="mm")

    y = 100
    # 2. Informações do Pedido
    draw.text((30, y), f"Data/Hora: {venda['data_hora']}", fill=c_gray, font=font_small)
    draw.text((width - 30, y), f"ID: #{venda['id'] % 100000}", fill=c_gray, font=font_small, anchor="ra")
    y += 22
    draw.text((30, y), f"Cliente: {venda['cliente']}", fill=c_dark, font=font_bold)
    y += 20
    draw.text((30, y), f"Telefone: {venda.get('telefone', 'N/A')}  |  Tipo: {venda.get('tipo_pedido', 'Retirada')}", fill=c_dark, font=font_text)
    y += 20
    draw.text((30, y), f"Horário de Retirada/Entrega: {venda.get('horario_retirada', 'Imediato')}", fill=c_orange, font=font_bold)
    
    y += 30
    # Linha Divisória
    draw.line([(30, y), (width - 30, y)], fill=(220, 220, 220), width=2)
    
    y += 15
    # 3. Tabela de Itens
    draw.text((30, y), "ITEM / DESCRIÇÃO", fill=c_gray, font=font_small)
    draw.text((width - 30, y), "QTD", fill=c_gray, font=font_small, anchor="ra")
    y += 20
    
    itens = []
    if venda['qtd_frango'] > 0: itens.append(("Frango Assado (c/ Batata)", venda['qtd_frango']))
    if venda['qtd_farofa'] > 0: itens.append(("Porção de Farofa Extra", venda['qtd_farofa']))
    if venda['qtd_batata'] > 0: itens.append(("Batata Extra", venda['qtd_batata']))
    if venda['qtd_refri'] > 0: itens.append(("Refrigerante 2L", venda['qtd_refri']))
    if venda.get('taxa_entrega', 0) > 0: itens.append(("Taxa de Entrega (Delivery)", f"R$ {venda['taxa_entrega']:.2f}"))

    for item_nome, qtd in itens:
        draw.text((30, y), f"• {item_nome}", fill=c_dark, font=font_text)
        draw.text((width - 30, y), f"{qtd}", fill=c_dark, font=font_bold, anchor="ra")
        y += 24

    y += 10
    # Linha Divisória Pontilhada
    draw.line([(30, y), (width - 30, y)], fill=(200, 200, 200), width=1)
    
    y += 20
    # 4. Pagamento e Total
    draw.text((30, y), f"Forma de Pagamento: {venda.get('forma_pagamento', 'N/I')}", fill=c_dark, font=font_text)
    y += 22
    
    if venda.get('troco', 0) > 0:
        draw.text((30, y), f"Valor Recebido: R$ {venda.get('valor_recebido', 0):.2f}  (Troco: R$ {venda['troco']:.2f})", fill=(39, 174, 96), font=font_bold)
        y += 24

    # Bloco com Fundo Destacado para o TOTAL
    y += 10
    draw.rectangle([30, y, width - 30, y + 45], fill=(254, 237, 222), outline=c_orange, width=1)
    draw.text((45, y + 22), "TOTAL DO PEDIDO:", fill=c_orange, font=font_bold, anchor="lm")
    draw.text((width - 45, y + 22), f"R$ {venda['valor_final']:.2f}", fill=c_orange, font=font_title, anchor="rm")
    
    y += 65
    if venda.get('observacao'):
        draw.text((30, y), f"📝 Obs: {venda['observacao']}", fill=c_dark, font=font_small)
        y += 25

    # 5. Rodapé
    y = height - 40
    draw.line([(30, y - 10), (width - 30, y - 10)], fill=(220, 220, 220), width=1)
    draw.text((width//2, y), "Obrigado pela preferência e bom apetite! ❤️", fill=c_gray, font=font_subtitle, anchor="mm")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def gerar_pdf_relatorio(df_dia, data_str):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1, textColor=colors.HexColor("#D35400"))
    story.append(Paragraph("<b>FRANGO ASSADO MV - RELATÓRIO DE VENDAS</b>", title_style))
    
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=11, alignment=1)
    story.append(Paragraph(f"Data do Relatório: {data_str} | 407 Norte - Palmas/TO", sub_style))
    story.append(Spacer(1, 15))

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
# INTERFACE GRÁFICA (STREAMLIT)
# ==========================================
st.title("🍗 Frango Assado MV")

configs_atuais = carregar_configuracoes()
historico_vendas = carregar_historico()

col_top1, col_top2 = st.columns([3, 1])
with col_top1:
    st.caption("📍 Endereço: 407 Norte (Em frente ao Supermercado da Matilde) | 📞 (63) 99297-1557")
with col_top2:
    if st.button("🔄 RESTAURAR EXEMPLOS (INCLUI MARKO POLLO)", type="secondary", use_container_width=True):
        salvar_historico(DADOS_EXEMPLO)
        st.success("Exemplos restaurados!")
        st.rerun()

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
    "🔥 Grelha & Status",
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
            st.write(" ")
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
        
        st.markdown("#### 💵 Fechamento de Caixa do Dia")
        pix_total = df_dia[df_dia['forma_pagamento'] == 'PIX']['valor_final'].sum()
        dinheiro_total = df_dia[df_dia['forma_pagamento'] == 'Dinheiro']['valor_final'].sum()
        credito_total = df_dia[df_dia['forma_pagamento'] == 'Cartão de Crédito']['valor_final'].sum()
        debito_total = df_dia[df_dia['forma_pagamento'] == 'Cartão de Débito']['valor_final'].sum()
        
        c_cx1, c_cx2, c_cx3, c_cx4 = st.columns(4)
        c_cx1.metric("📲 Total no PIX", f"R$ {pix_total:.2f}")
        c_cx2.metric("💵 Dinheiro na Gaveta", f"R$ {dinheiro_total:.2f}")
        c_cx3.metric("💳 Cartão de Crédito", f"R$ {credito_total:.2f}")
        c_cx4.metric("💳 Cartão de Débito", f"R$ {debito_total:.2f}")
    else:
        st.info("Nenhuma venda registrada ainda.")

# ------------------------------------------
# ABA GRELHA & STATUS
# ------------------------------------------
with aba_grelha:
    st.markdown("### 🔥 Controle de Grelha e Status")
    
    if historico_vendas:
        df_grelha = pd.DataFrame(historico_vendas)
        df_grelha['data_str'] = pd.to_datetime(df_grelha['data_hora'], format="%d/%m/%Y %H:%M").dt.strftime("%d/%m/%Y")
        
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        df_hoje = df_grelha[df_grelha['data_str'] == data_hoje]
        
        if not df_hoje.empty:
            horarios = sorted(df_hoje['horario_retirada'].unique())
            
            for h in horarios:
                pedidos_horario = df_hoje[df_hoje['horario_retirada'] == h]
                qtd_frangos_horario = pedidos_horario['qtd_frango'].sum()
                
                with st.expander(f"⏰ Horário {h} — {len(pedidos_horario)} pedido(s) | 🍗 {qtd_frangos_horario} frango(s)", expanded=True):
                    for _, ped in pedidos_horario.iterrows():
                        ped_dict = ped.to_dict()
                        col_p1, col_p2, col_p3 = st.columns([3, 3, 4])
                        col_p1.write(f"👤 **{ped['cliente']}** ({ped['tipo_pedido']})")
                        col_p2.write(f"🍗 {ped['qtd_frango']} Frango(s) | 💰 R$ {ped['valor_final']:.2f}")
                        
                        link_pronto = gerar_link_whatsapp(ped_dict, status="pronto")
                        link_entrega = gerar_link_whatsapp(ped_dict, status="entrega")
                        
                        with col_p3:
                            if ped['tipo_pedido'] == "Retirada no Local" and link_pronto:
                                st.markdown(f"[✅ **Avisar: PRONTO P/ RETIRADA**]({link_pronto})")
                            elif ped['tipo_pedido'] == "Entrega (Delivery)" and link_entrega:
                                st.markdown(f"[🛵 **Avisar: SAIU P/ ENTREGA**]({link_entrega})")
                            else:
                                st.caption("Sem WhatsApp")
                        
                        if ped.get('observacao'):
                            st.caption(f"📌 Obs: {ped['observacao']}")
                        st.divider()
        else:
            st.info("Nenhum pedido registrado para o dia de hoje.")
    else:
        st.info("Nenhum pedido cadastrado no sistema.")

# ------------------------------------------
# ABA 1: NOVA VENDA (COM CUPOM EM IMAGEM)
# ------------------------------------------
with aba1:
    st.markdown("### 📝 Registrar Novo Pedido")
    
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        if st.button("🧪 Carregar Dados do Marko Pollo (Teste)", type="secondary"):
            st.session_state['input_nome'] = "Marko Pollo"
            st.session_state['input_tel'] = "63992543227"
            st.rerun()

    val_nome = st.session_state.get('input_nome', '')
    val_tel = st.session_state.get('input_tel', '')

    col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
    with col_c1:
        cliente_nome = st.text_input("Nome do Cliente", value=val_nome, placeholder="Ex: Marko Pollo")
    with col_c2:
        telefone = st.text_input("WhatsApp (DDD+Número)", value=val_tel, placeholder="63992543227")
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
        valor_final = st.number_input("💰 Valor Final Cobrado", min_value=0.0, value=float(subtotal), step=1.0, format="%.2f")
    with col_v3:
        forma_pagamento = st.selectbox("Forma de Pagamento", ["PIX", "Dinheiro", "Cartão de Crédito", "Cartão de Débito"])

    valor_recebido = 0.0
    troco = 0.0
    if forma_pagamento == "Dinheiro":
        col_tr1, col_tr2 = st.columns(2)
        with col_tr1:
            valor_recebido = st.number_input("Valor Recebido em Dinheiro (R$)", min_value=0.0, value=float(valor_final), step=5.0)
        with col_tr2:
            troco = max(0.0, valor_recebido - valor_final)
            st.metric("💵 Troco a Devolver", f"R$ {troco:.2f}")

    obs = st.text_input("Observações / Endereço de Entrega", placeholder="Ex: Alameda 2, Casa 15 / Sem pimenta")

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
            'valor_recebido': round(valor_recebido, 2),
            'troco': round(troco, 2),
            'forma_pagamento': forma_pagamento,
            'observacao': obs
        }
        
        historico_vendas.insert(0, nova_venda)
        salvar_historico(historico_vendas)
        
        st.session_state['input_nome'] = ""
        st.session_state['input_tel'] = ""
        st.session_state['ultima_venda'] = nova_venda
        st.success(f"Venda registrada com sucesso! Total: R$ {valor_final:.2f}")
        st.rerun()

    # ÁREA DO RECIBO APÓS FINALIZAR VENDA
    if 'ultima_venda' in st.session_state:
        uv = st.session_state['ultima_venda']
        st.markdown("---")
        
        col_uv_head1, col_uv_head2 = st.columns([3, 1])
        with col_uv_head1:
            st.markdown(f"#### 📄 Comprovante do Pedido: **{uv['cliente']}**")
        with col_uv_head2:
            if st.button("✖️ Iniciar Novo Pedido", type="secondary"):
                del st.session_state['ultima_venda']
                st.rerun()

        col_act1, col_act2 = st.columns([1, 1])
        
        with col_act1:
            link_zap = gerar_link_whatsapp(uv, status="confirmado")
            if link_zap:
                st.markdown(f"👉 [📲 **Enviar Confirmação no WhatsApp**]({link_zap})")
            
            # Gerar e exibir a imagem do cupom na tela
            img_buffer = gerar_cupom_imagem(uv)
            st.image(img_buffer, caption="Preview do Cupom", width=380)
            
        with col_act2:
            st.write(" ")
            st.write(" ")
            st.download_button(
                label="🖼️ BAIXAR CUPOM EM IMAGEM (PNG)",
                data=img_buffer,
                file_name=f"cupom_{uv['cliente'].replace(' ', '_')}.png",
                mime="image/png",
                type="primary",
                use_container_width=True
            )

# ------------------------------------------
# ABA 2: CLIENTES & FIDELIDADE
# ------------------------------------------
with aba2:
    st.markdown("### 👥 Ranking de Clientes e Cartão Fidelidade")
    meta = configs_atuais.get('META_FIDELIDADE', 10)
    
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
                
                st.progress(progresso, text=f"Fidelidade: {frangos_acumulados}/{meta} frangos")
                if frangos_acumulados >= meta:
                    st.success("🎉 Cliente elegível para brinde/desconto!")
                st.divider()

# ------------------------------------------
# ABA 3: HISTÓRICO & EDIÇÃO
# ------------------------------------------
with aba3:
    st.markdown("### 📜 Histórico de Vendas (Envio WhatsApp e Edição)")
    
    if historico_vendas:
        for idx, item in enumerate(historico_vendas):
            with st.expander(f"🗓️ {item['data_hora']} - {item['cliente']} | R$ {item['valor_final']:.2f} ({item.get('forma_pagamento', 'N/I')})"):
                
                col_h_act1, col_h_act2 = st.columns(2)
                with col_h_act1:
                    link_zap_hist = gerar_link_whatsapp(item, status="confirmado")
                    if link_zap_hist:
                        st.markdown(f"📲 [**Reenviar Comprovante no WhatsApp**]({link_zap_hist})")
                
                with col_h_act2:
                    img_hist_buffer = gerar_cupom_imagem(item)
                    st.download_button(
                        label="🖼️ Baixar Cupom em Imagem",
                        data=img_hist_buffer,
                        file_name=f"cupom_{item['id']}.png",
                        mime="image/png",
                        key=f"btn_img_{item['id']}"
                    )

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
                        st.success("Atualizado!")
                        st.rerun()

                if st.button(f"❌ Excluir Venda (#{item['id']})", key=f"del_{item['id']}"):
                    historico_vendas.pop(idx)
                    salvar_historico(historico_vendas)
                    st.success("Removido!")
                    st.rerun()
    else:
        st.info("Nenhum registro encontrado.")

# ------------------------------------------
# ABA 4: CONFIGURAÇÕES DE PREÇOS
# ------------------------------------------
with aba4:
    st.markdown("### ⚙️ Configurações de Preços e Estoque")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        p_frango = st.number_input("Preço Frango Assado (R$)", value=float(configs_atuais['PRECO_FRANGO']))
        p_farofa = st.number_input("Preço Porção Farofa (R$)", value=float(configs_atuais['PRECO_FAROFA']))
        est_dia = st.number_input("🔥 Estoque Inicial (Dia)", value=int(configs_atuais.get('ESTOQUE_INICIAL', 40)), step=5)
    with col_p2:
        p_batata = st.number_input("Preço Batata Extra (R$)", value=float(configs_atuais['PRECO_BATATA_EXTRA']))
        p_refri = st.number_input("Preço Refrigerante (R$)", value=float(configs_atuais['PRECO_REFRIGERANTE']))
        meta_fid = st.number_input("Meta Cartão Fidelidade", value=int(configs_atuais.get('META_FIDELIDADE', 10)), step=1)

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
# ABA 5: MANUAL E DICAS
# ------------------------------------------
with aba_ajuda:
    st.markdown("### 📖 Guia de Uso do Sistema")
    st.markdown("""
    * **Cupom em Imagem:** Ao registrar a venda, a imagem do comprovante é exibida na tela. Clique em **🖼️ BAIXAR CUPOM EM IMAGEM (PNG)** para guardar ou enviar direto pelo WhatsApp.
    * **Disparo na Grelha:** Na aba `🔥 Grelha & Status`, use os botões rápidos para avisar o cliente assim que o frango estiver pronto para busca ou a caminho da entrega.
    * **Relatório em PDF:** Baixe o fechamento de caixa na aba `📊 Dashboard & PDF`.
    """)
