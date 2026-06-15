import sys
import re

# ==========================================
# 1. ANÁLISE LÉXICA (Scanner / Picareta)
# ==========================================
# O Lexer é responsável por ler o texto bruto e dividi-lo em "Tokens" (palavras compreensíveis).
# Usamos Expressões Regulares (Regex) para identificar cada pedaço do código.
TOKEN_REGEX = [
    # Tipos Primitivos de Dados
    ('T_INT', r'\bmine\b'),             # Inteiros
    ('T_FLOAT', r'\benderman\b'),       # Ponto flutuante
    ('T_CHAR', r'\bsteve\b'),           # Caracteres
    ('T_BOOL', r'\bredstone\b'),        # Booleanos
    
    # Estruturas Complexas
    ('T_STRUCT', r'\bcraft\b'),         # Palavra-chave para criar Structs
    ('T_DOT', r'\.'),                   # Ponto usado para acessar atributos (ex: entrega.nota)
    
    # Funções e Retorno
    ('T_FUNC', r'\bfornalha\b'),        # Declaração de função
    ('T_RETURN', r'\bretorna\b'),       # Retorno de função
    ('T_PRINT', r'\bmostra\b'),         # Função embutida para imprimir na tela
    
    # Controle de Fluxo
    ('T_IF', r'\bdinnerbone\b'),        # Estrutura condicional (If)
    ('T_ELSE', r'\bcreeper\b'),         # Caminho alternativo (Else)
    ('T_WHILE', r'\brepetidor\b'),      # Laço de repetição (While)
    ('T_GOTO', r'\benderpearl\b'),      # Salto incondicional (Go To)
    
    # Controle de Pilha e Parâmetros (Assembly de baixo nível)
    ('T_PARAM', r'\bloot\b'),           # Lê o primeiro parâmetro recebido pela função
    ('T_PUSH', r'\bbau_guardar\b'),     # Salva um valor na Stack (push)
    ('T_POP', r'\bbau_pegar\b'),        # Recupera um valor da Stack (pop)
    
    # Rótulos (Labels) para o Go To
    ('T_LABEL_DEF', r'@[a-zA-Z_][a-zA-Z0-9_]*:'), # Ponto de aterrissagem (ex: @base:)
    ('T_LABEL_REF', r'@[a-zA-Z_][a-zA-Z0-9_]*'),  # Destino do pulo (ex: @base)
    
    # Valores e Símbolos
    ('T_TRUE', r'\bverdadeiro\b'),      # Booleano True
    ('T_FALSE', r'\bfalso\b'),          # Booleano False
    ('T_NUMBER', r'\b\d+\b'),           # Qualquer número inteiro
    ('T_STRING_VAL', r'"[^"]*"'),       # Textos entre aspas duplas
    ('T_IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'), # Nomes de variáveis criadas pelo usuário
    
    # Operadores Matemáticos e Lógicos
    ('T_EQUAL', r'=='),                 # Comparação de igualdade
    ('T_ASSIGN', r='='),                # Atribuição de valor
    ('T_LESS', r'<'),                   # Menor que
    ('T_LBRACKET', r'\['),              # Abre colchetes (Vetores e blocos)
    ('T_RBRACKET', r'\]'),              # Fecha colchetes
    ('T_LPAREN', r'\('),                # Abre parênteses
    ('T_RPAREN', r'\)'),                # Fecha parênteses
    ('T_ADD', r'\+'),                   # Adição
    ('T_SUB', r'\-'),                   # Subtração
    ('T_SEMI', r';'),                   # Fim de instrução
    ('T_COMMA', r','),                  # Separador
    
    # Ignorados pelo Compilador
    ('T_COMMENT', r'#.*'),              # Ignora tudo após o '#' até o fim da linha
    ('T_SKIP', r'[ \t\n\r]+'),          # Ignora espaços em branco e quebras de linha
]

def analisar_lexico(codigo):
    """
    Varre o código fonte caractere por caractere.
    Se encontrar um padrão válido, transforma em Token. Se achar um caractere alienígena, para o programa.
    """
    tokens = []
    pos = 0
    while pos < len(codigo):
        match = None
        for nome_token, padrao in TOKEN_REGEX:
            regex = re.compile(padrao)
            match = regex.match(codigo, pos)
            if match:
                texto = match.group(0)
                # Não guardamos espaços nem comentários, eles não vão para o Assembly
                if nome_token not in ['T_SKIP', 'T_COMMENT']:
                    tokens.append((nome_token, texto))
                pos = match.end(0)
                break
        if not match:
            print(f"Erro Léxico: Caractere inválido na posição {pos}")
            sys.exit(1)
    return tokens

# ==========================================
# 2, 3 e 6. SINTÁTICA, SEMÂNTICA E GERAÇÃO DE CÓDIGO
# ==========================================
def compilar_para_assembly(tokens):
    """
    O Parser: Transforma a lista de tokens em instruções do processador x86.
    O Assembly no Linux é dividido em 3 seções:
    - .data: Para coisas que não mudam (ex: Textos do print).
    - .bss: Para alocar espaço de variáveis na memória RAM (zeradas).
    - .text: A lógica do programa (os comandos reais).
    """
    asm_data = ["section .data"]
    asm_bss = ["section .bss"]
    asm_text = ["section .text", "    global _start", "_start:"]
    
    tipos_primitivos = ('T_INT', 'T_FLOAT', 'T_CHAR', 'T_BOOL')
    
    # Dicionários para ajudar o compilador a lembrar as estruturas matemáticas do usuário
    tabela_structs = {}  # Guarda o molde da Struct (quais atributos ela tem e a distância em bytes de cada um)
    mapa_instancias = {} # Associa o nome de uma variável ao seu molde (ex: entrega_atual é do tipo RelacaoUsuarioPedido)
    
    # ---------------------------------------------------------
    # PASSO 1: O Reconhecimento de Structs (Aprender o Molde)
    # ---------------------------------------------------------
    # Antes de alocar memória, precisamos varrer o código para descobrir como as Structs do usuário são feitas.
    pos = 0
    while pos < len(tokens):
        if tokens[pos][0] == 'T_STRUCT':
            struct_name = tokens[pos+1][1]
            tabela_structs[struct_name] = {}
            offset = 0 # Distância em bytes a partir do endereço principal
            pos += 3   # Pula 'craft', 'NomeDaStruct', '['
            
            # Lê todos os atributos internos da struct
            while tokens[pos][0] != 'T_RBRACKET':
                if tokens[pos][0] in tipos_primitivos and tokens[pos+1][0] == 'T_IDENTIFIER':
                    attr_name = tokens[pos+1][1]
                    tabela_structs[struct_name][attr_name] = offset
                    offset += 4 # No x86 de 32 bits, cada variável ocupa 4 bytes
                    pos += 3
                else:
                    pos += 1
        pos += 1

    # ---------------------------------------------------------
    # PASSO 2: Alocação de Memória RAM (A seção .bss)
    # ---------------------------------------------------------
    # Agora que sabemos os moldes, vamos varrer de novo para reservar espaço na RAM para todas as variáveis do usuário.
    for i, t in enumerate(tokens):
        # 2.1 - Aloca Vetores (ex: mine inventario[3];) -> Reserva N slots de 4 bytes.
        if t[0] == 'T_IDENTIFIER' and i > 0 and tokens[i-1][0] in tipos_primitivos and i+1 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET':
            tamanho = tokens[i+2][1]
            asm_bss.append(f"    {t[1]} resd {tamanho} ; Aloca um vetor de {tamanho} posições")
            
        # 2.2 - Aloca Variáveis Primitivas (ex: mine x;) -> Reserva 1 slot (resd 1).
        elif t[0] == 'T_IDENTIFIER' and i > 0 and tokens[i-1][0] in tipos_primitivos and not (i > 1 and tokens[i-2][0] == 'T_LPAREN') and not (i+1 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET'):
            asm_bss.append(f"    {t[1]} resd 1 ; Aloca variável global")
            
        # 2.3 - Aloca Instâncias de Structs (ex: Relacao entrega;) -> Calcula o total de bytes e reserva (resb).
        elif t[0] == 'T_IDENTIFIER' and t[1] in tabela_structs:
            if i+1 < len(tokens) and tokens[i+1][0] == 'T_IDENTIFIER':
                inst_name = tokens[i+1][1]
                mapa_instancias[inst_name] = t[1]
                tamanho_total = len(tabela_structs[t[1]]) * 4
                asm_bss.append(f"    {inst_name} resb {tamanho_total} ; Aloca bloco para a struct {t[1]}")

    str_count = 0
    pilha_blocos = [] # Ajuda a rastrear IFs e Loops para saber onde colocar os fechamentos ']'
    i = 0
    
    # ---------------------------------------------------------
    # PASSO 3: A Geração da Lógica (A seção .text)
    # ---------------------------------------------------------
    while i < len(tokens):
        
        # Ignora as palavras de Tipos de Dados na hora de executar (já foram pro .bss)
        if tokens[i][0] in tipos_primitivos:
            if i+2 < len(tokens) and tokens[i+2][0] == 'T_LBRACKET':
                while tokens[i][0] != 'T_SEMI': i += 1
                i += 1
                continue
            i += 1
            continue

        # Ignora a definição de Structs (já foram mapeadas no Passo 1)
        if tokens[i][0] == 'T_STRUCT':
            while tokens[i][0] != 'T_RBRACKET': i += 1
            i += 1
            continue
            
        # Ignora a criação da variável da struct (já foi pro .bss no Passo 2)
        if tokens[i][0] == 'T_IDENTIFIER' and tokens[i][1] in tabela_structs:
            i += 3 
            continue

        # Regra: Atribuição dentro de um Vetor (ex: inventario[2] = 5;)
        if tokens[i][0] == 'T_IDENTIFIER' and i+4 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET' and tokens[i+4][0] == 'T_ASSIGN':
            vetor_name = tokens[i][1]
            indice = int(tokens[i+2][1])
            valor = tokens[i+5][1]
            
            # A mágica do Array: Endereço Base + (Índice * 4 bytes)
            offset = indice * 4
            asm_text.append(f"    ; {vetor_name}[{indice}] = {valor}")
            if valor.isdigit():
                asm_text.append(f"    mov dword [{vetor_name} + {offset}], {valor}")
            
            i += 7
            continue

        # Regra: Atribuição dentro de uma Struct (ex: entrega.nota = 5;)
        if tokens[i][0] == 'T_IDENTIFIER' and i+2 < len(tokens) and tokens[i+1][0] == 'T_DOT' and tokens[i+3][0] == 'T_ASSIGN':
            inst_name = tokens[i][1]
            attr_name = tokens[i+2][1]
            struct_type = mapa_instancias[inst_name]
            offset = tabela_structs[struct_type][attr_name] # Pega a distância mapeada no Passo 1
            valor = tokens[i+4][1]
            
            asm_text.append(f"    ; {inst_name}.{attr_name} = {valor}")
            if valor.isdigit(): 
                asm_text.append(f"    mov dword [{inst_name} + {offset}], {valor}")
            elif valor == 'verdadeiro':
                asm_text.append(f"    mov dword [{inst_name} + {offset}], 1") # Booleano vira bit
            
            i += 6
            continue

        # Regra: Atribuição de Variável Normal (ex: x = 10;)
        if tokens[i][0] == 'T_IDENTIFIER' and i+1 < len(tokens) and tokens[i+1][0] == 'T_ASSIGN':
            var_dest = tokens[i][1]
            if i+3 < len(tokens) and tokens[i+2][0] in ('T_NUMBER', 'T_TRUE', 'T_FALSE') and tokens[i+3][0] == 'T_SEMI':
                op1 = tokens[i+2][1]
                asm_text.append(f"    ; {var_dest} = {op1}")
                if op1.isdigit(): asm_text.append(f"    mov eax, {op1}")
                elif op1 == 'verdadeiro': asm_text.append(f"    mov eax, 1")
                elif op1 == 'falso': asm_text.append(f"    mov eax, 0")
                asm_text.append(f"    mov [{var_dest}], eax")
                i += 4
                continue

        # Regra: Imprimir Texto na tela usando o Syscall do Linux
        elif tokens[i][0] == 'T_PRINT' and tokens[i+1][0] == 'T_LPAREN' and tokens[i+2][0] == 'T_STRING_VAL':
            texto = tokens[i+2][1].strip('"')
            label_str = f"msg_{str_count}"
            label_len = f"len_{str_count}"
            str_count += 1
            
            # Salva o texto blindado com aspas duplas na seção .data e calcula o tamanho dele
            asm_data.append(f'    {label_str} db "{texto}", 10') 
            asm_data.append(f"    {label_len} equ $ - {label_str}")
            
            # Prepara a interrupção 0x80 do Linux para escrever (sys_write)
            asm_text.append(f"    ; mostra(\"{texto}\")")
            asm_text.append(f"    mov eax, 4           ; Syscall 4 = Write")
            asm_text.append(f"    mov ebx, 1           ; Arquivo 1 = Tela (Monitor)")
            asm_text.append(f"    mov ecx, {label_str} ; O texto")
            asm_text.append(f"    mov edx, {label_len} ; O tamanho")
            asm_text.append(f"    int 0x80             ; Chama o kernel do Linux")
            i += 4
            if i < len(tokens) and tokens[i][0] == 'T_SEMI': i += 1
            
        else:
            i += 1

    # Regra Final: Finaliza o executável de forma segura (sys_exit)
    asm_text.append("\n    ; Encerrando o programa limpo")
    asm_text.append("    mov eax, 1     ; Syscall 1 = Exit")
    asm_text.append("    xor ebx, ebx   ; Zera o EBX (Return 0)")
    asm_text.append("    int 0x80       ; Chama o kernel")
    
    # Junta as três seções em um único arquivo de texto gigante
    return "\n".join(asm_data) + "\n\n" + "\n".join(asm_bss) + "\n\n" + "\n".join(asm_text)

# ==========================================
# FLUXO PRINCIPAL
# ==========================================
if __name__ == "__main__":
    codigo_fonte = """
    # Este código final prova todos os conceitos complexos integrados:
    mine inventario[3];
    inventario[0] = 64; 
    
    craft RelacaoUsuarioPedido [
        mine avaliacao;
    ]
    RelacaoUsuarioPedido entrega;
    entrega.avaliacao = 5;

    mostra("Sistema Inicializado e Memoria Alocada. O Compilador MineScript e um sucesso!");
    """
    
    print("Iniciando mineração dos tokens...")
    tokens = analisar_lexico(codigo_fonte)
    
    print("Craftando executável x86...")
    codigo_asm = compilar_para_assembly(tokens)
    
    with open("saida.asm", "w") as f:
        f.write(codigo_asm)
        
    print("Pronto! Arquivo .asm atualizado com sucesso.")