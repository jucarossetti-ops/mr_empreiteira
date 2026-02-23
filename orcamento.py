import streamlit as st
import google.generativeai as genai
import urllib.parse

# --- CONEXÃO SEGURA ---
# O Streamlit busca automaticamente a chave nos "Secrets"
if "API_KEY" in st.secrets:
    API_KEY = st.secrets["API_KEY"]
else:
    # Caso você ainda esteja rodando local sem o arquivo secrets.toml
    API_KEY = "COLOQUE_SUA_CHAVE_AQUI_APENAS_PARA_TESTE_LOCAL"

genai.configure(api_key=API_KEY)

st.set_page_config(page_title="Orçador MR. EMPREITEIRA", layout="centered")

def buscar_modelo_oficial():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'flash' in m.name: return m.name
        return "models/gemini-1.5-flash"
    except: return "models/gemini-1.5-flash"

st.title("🏗️ Orçador MR. EMPREITEIRA")

# --- MEMÓRIA ---
if 'carrinho' not in st.session_state: st.session_state.carrinho = []

# --- DADOS DO CLIENTE ---
with st.expander("👤 Dados do Cliente e Local", expanded=True):
    nome_cliente = st.text_input("Nome do Cliente:", placeholder="Ex: Maria Aparecida")
    bairro = st.text_input("Localização/Bairro:", placeholder="Ex: Nova Brasília")

# --- ADIÇÃO DE SERVIÇOS ---
with st.form("add_servico", clear_on_submit=True):
    st.subheader("➕ Incluir Serviço")
    col1, col2 = st.columns([2, 1])
    serv = col1.text_input("Descrição do Serviço:", placeholder="Ex: Construção de Muro de Alvenaria")
    qtd = col2.text_input("Qtd/Medida:", placeholder="Ex: 10 metros lineares")
    if st.form_submit_button("ADICIONAR ITEM"):
        if serv:
            st.session_state.carrinho.append({"s": serv, "q": qtd})
            st.rerun()

# --- LISTA E CÁLCULO ---
if st.session_state.carrinho:
    st.write("---")
    st.subheader("📋 Lista de Serviços Selecionados")
    texto_servicos_lista = ""
    for i, item in enumerate(st.session_state.carrinho):
        st.write(f"✅ {item['s']} - {item['q']}")
        texto_servicos_lista += f"- {item['s']} (Qtd: {item['q']})\n"
    
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.carrinho = []
        st.rerun()

    if st.button("💰 CALCULAR VALORES TOTAIS"):
        nome_modelo = buscar_modelo_oficial()
        
        # PROMPT MELHORADO PARA EVITAR VALORES ABSURDOS
        prompt = (
            f"Você é um engenheiro de custos sênior em Joinville-SC. "
            f"Calcule o valor total de MÃO DE OBRA para:\n{texto_servicos_lista}\n"
            f"Local: {bairro}.\n"
            f"ATENÇÃO: Considere que metros (m) em muros referem-se a construção do zero (fundação, alvenaria e acabamento). "
            f"Use a tabela CUB-SC e preços de mercado de Joinville. Não subestime o valor.\n"
            f"Retorne APENAS os valores totais somados no formato EXATO abaixo:\n"
            f"COMPETITIVO: valor\n"
            f"SUGERIDO: valor\n"
            f"JUSTO: valor"
        )

        try:
            with st.spinner('IA Calculando preços...'):
                model = genai.GenerativeModel(nome_modelo)
                response = model.generate_content(prompt)
                res = response.text.upper()
                
                linhas = res.split('\n')
                valores = {}
                for l in linhas:
                    if ':' in l:
                        val = l.split(':')[-1].strip().replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
                        if 'COMPETITIVO' in l: valores['Competitivo'] = val
                        if 'SUGERIDO' in l: valores['Sugerido'] = val
                        if 'JUSTO' in l: valores['Justo'] = val

                st.subheader("📊 Selecione o orçamento para enviar:")
                c1, c2, c3 = st.columns(3)
                opcoes = [("Competitivo", c1), ("Sugerido", c2), ("Justo", c3)]

                for tipo, col in opcoes:
                    valor_cru = valores.get(tipo, "0.00")
                    # Formatação brasileira de moeda
                    try:
                        v_float = float(valor_cru)
                        valor_formatado = f"R$ {v_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except:
                        valor_formatado = f"R$ {valor_cru}"
                    
                    with col:
                        st.metric(tipo, valor_formatado)
                        msg_zap = (
                            f"ORÇAMENTO DE MÃO DE OBRA\n"
                            f"Empresa: MR. EMPREITEIRA\n"
                            f"----------------------------\n"
                            f"Cliente: {nome_cliente}\n"
                            f"Serviços:\n{texto_servicos_lista}"
                            f"Localização: {bairro}\n"
                            f"----------------------------\n"
                            f"VALOR TOTAL: {valor_formatado}\n"
                            f"----------------------------\n"
                            f"📍 Validade do Orçamento: 30 dias.\n"
                            f"📍 Joinville - SC"
                        )
                        link = f"https://wa.me/?text={urllib.parse.quote(msg_zap)}"
                        st.markdown(f'<a href="{link}" target="_blank" style="text-decoration:none;"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:8px; cursor:pointer; font-weight:bold;">ENVIAR {tipo.upper()}</button></a>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")