import sys
import re

# ==========================================
# 1. ANÁLISE LÉXICA (Scanner)
# ==========================================
TOKEN_REGEX = [
    ('T_INT', r'\bmine\b'),
    ('T_FLOAT', r'\benderman\b'),
    ('T_CHAR', r'\bsteve\b'),
    ('T_BOOL', r'\bredstone\b'),
    ('T_STRUCT', r'\bcraft\b'),         
    ('T_DOT', r'\.'),                   
    
    ('T_FUNC', r'\bfornalha\b'),        
    ('T_RETURN', r'\bretorna\b'),       
    ('T_PRINT', r'\bmostra\b'),
    
    ('T_IF', r'\bdinnerbone\b'),
    ('T_ELSE', r'\bcreeper\b'),         
    ('T_WHILE', r'\brepetidor\b'),
    ('T_GOTO', r'\benderpearl\b'),      
    
    ('T_PARAM', r'\bloot\b'),           
    ('T_PUSH', r'\bbau_guardar\b'),     
    ('T_POP', r'\bbau_pegar\b'),        
    
    ('T_LABEL_DEF', r'@[a-zA-Z_][a-zA-Z0-9_]*:'),
    ('T_LABEL_REF', r'@[a-zA-Z_][a-zA-Z0-9_]*'),
    
    ('T_TRUE', r'\bverdadeiro\b'),      
    ('T_FALSE', r'\bfalso\b'),          
    ('T_NUMBER', r'\b\d+\b'),
    ('T_STRING_VAL', r'"[^"]*"'),
    ('T_IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),
    ('T_EQUAL', r'=='),                 
    ('T_ASSIGN', r'='),                 
    ('T_LESS', r'<'),
    ('T_LBRACKET', r'\['),
    ('T_RBRACKET', r'\]'),
    ('T_LPAREN', r'\('),
    ('T_RPAREN', r'\)'),
    ('T_ADD', r'\+'),
    ('T_SUB', r'\-'),                   
    ('T_SEMI', r';'),
    ('T_COMMA', r','),                  
    ('T_COMMENT', r'#.*'),              
    ('T_SKIP', r'[ \t\n\r]+'),
]

def analisar_lexico(codigo):
    tokens = []
    pos = 0
    while pos < len(codigo):
        match = None
        for nome_token, padrao in TOKEN_REGEX:
            regex = re.compile(padrao)
            match = regex.match(codigo, pos)
            if match:
                texto = match.group(0)
                if nome_token not in ['T_SKIP', 'T_COMMENT']:
                    tokens.append((nome_token, texto))
                pos = match.end(0)
                break
        if not match:
            print(f"Erro Léxico: Caractere inválido na posição {pos}")
            sys.exit(1)
    return tokens

# ==========================================
# 2, 3 e 6. SINTÁTICA, SEMÂNTICA E ASSEMBLY
# ==========================================
def compilar_para_assembly(tokens):
    asm_data = ["section .data"]
    asm_bss = ["section .bss"]
    asm_text = ["section .text", "    global _start", "_start:"]
    
    tipos_primitivos = ('T_INT', 'T_FLOAT', 'T_CHAR', 'T_BOOL')
    tabela_structs = {}
    mapa_instancias = {}
    
    # PASSO 1: Mapeamento de Structs
    pos = 0
    while pos < len(tokens):
        if tokens[pos][0] == 'T_STRUCT':
            struct_name = tokens[pos+1][1]
            tabela_structs[struct_name] = {}
            offset = 0
            pos += 3 
            while tokens[pos][0] != 'T_RBRACKET':
                if tokens[pos][0] in tipos_primitivos and tokens[pos+1][0] == 'T_IDENTIFIER':
                    attr_name = tokens[pos+1][1]
                    tabela_structs[struct_name][attr_name] = offset
                    offset += 4 
                    pos += 3
                else:
                    pos += 1
        pos += 1

    # PASSO 2: Alocação no .BSS (Variáveis, Vetores e Structs)
    for i, t in enumerate(tokens):
        # NOVO: Aloca Vetores (ex: mine inventario[5];)
        if t[0] == 'T_IDENTIFIER' and i > 0 and tokens[i-1][0] in tipos_primitivos and i+1 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET':
            tamanho = tokens[i+2][1]
            asm_bss.append(f"    {t[1]} resd {tamanho} ; Vetor com {tamanho} slots de 4 bytes")
            
        # Aloca variáveis primitivas simples
        elif t[0] == 'T_IDENTIFIER' and i > 0 and tokens[i-1][0] in tipos_primitivos and not (i > 1 and tokens[i-2][0] == 'T_LPAREN') and not (i+1 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET'):
            asm_bss.append(f"    {t[1]} resd 1")
            
        # Aloca as instâncias das Structs
        elif t[0] == 'T_IDENTIFIER' and t[1] in tabela_structs:
            if i+1 < len(tokens) and tokens[i+1][0] == 'T_IDENTIFIER':
                inst_name = tokens[i+1][1]
                mapa_instancias[inst_name] = t[1]
                tamanho_total = len(tabela_structs[t[1]]) * 4
                asm_bss.append(f"    {inst_name} resb {tamanho_total} ; Struct {t[1]}")

    str_count = 0
    pilha_blocos = [] 
    i = 0
    
    # PASSO 3: Geração de Código Final
    while i < len(tokens):
        
        # Pula as palavras de Tipos de Dados se não forem declaração de função
        if tokens[i][0] in tipos_primitivos:
            # NOVO: Pula a declaração completa do Vetor no código de execução
            if i+2 < len(tokens) and tokens[i+2][0] == 'T_LBRACKET':
                while tokens[i][0] != 'T_SEMI': i += 1
                i += 1
                continue
            i += 1
            continue

        if tokens[i][0] == 'T_STRUCT':
            while tokens[i][0] != 'T_RBRACKET': i += 1
            i += 1
            continue
            
        if tokens[i][0] == 'T_IDENTIFIER' and tokens[i][1] in tabela_structs:
            i += 3 
            continue

        # NOVO: Atribuição em Posição do Vetor (ex: inventario[2] = 64;)
        if tokens[i][0] == 'T_IDENTIFIER' and i+4 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET' and tokens[i+4][0] == 'T_ASSIGN':
            vetor_name = tokens[i][1]
            indice = int(tokens[i+2][1])
            valor = tokens[i+5][1]
            
            offset = indice * 4  # A mágica da indexação em memória contígua
            
            asm_text.append(f"    ; {vetor_name}[{indice}] = {valor}")
            if valor.isdigit():
                asm_text.append(f"    mov dword [{vetor_name} + {offset}], {valor}")
            
            i += 7
            continue

        # Atribuição de Atributo de Struct
        if tokens[i][0] == 'T_IDENTIFIER' and i+2 < len(tokens) and tokens[i+1][0] == 'T_DOT' and tokens[i+3][0] == 'T_ASSIGN':
            inst_name = tokens[i][1]
            attr_name = tokens[i+2][1]
            struct_type = mapa_instancias[inst_name]
            offset = tabela_structs[struct_type][attr_name]
            valor = tokens[i+4][1]
            
            asm_text.append(f"    ; {inst_name}.{attr_name} = {valor}")
            if valor.isdigit(): 
                asm_text.append(f"    mov dword [{inst_name} + {offset}], {valor}")
            elif valor == 'verdadeiro':
                asm_text.append(f"    mov dword [{inst_name} + {offset}], 1")
            
            i += 6
            continue

        # Atribuição Primitiva Normal
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

        # Imprimir Texto na tela
        elif tokens[i][0] == 'T_PRINT' and tokens[i+1][0] == 'T_LPAREN' and tokens[i+2][0] == 'T_STRING_VAL':
            texto = tokens[i+2][1].strip('"')
            label_str = f"msg_{str_count}"
            label_len = f"len_{str_count}"
            str_count += 1
            asm_data.append(f'    {label_str} db "{texto}", 10')
            asm_data.append(f"    {label_len} equ $ - {label_str}")
            asm_text.append(f"    ; mostra(\"{texto}\")")
            asm_text.append(f"    mov eax, 4")
            asm_text.append(f"    mov ebx, 1")
            asm_text.append(f"    mov ecx, {label_str}")
            asm_text.append(f"    mov edx, {label_len}")
            asm_text.append(f"    int 0x80")
            i += 4
            if i < len(tokens) and tokens[i][0] == 'T_SEMI': i += 1
            
        else:
            i += 1

    asm_text.append("\n    ; Encerrando o programa")
    asm_text.append("    mov eax, 1")
    asm_text.append("    xor ebx, ebx")
    asm_text.append("    int 0x80")
    
    return "\n".join(asm_data) + "\n\n" + "\n".join(asm_bss) + "\n\n" + "\n".join(asm_text)

# ==========================================
# FLUXO PRINCIPAL (Testando Vetores em Ação)
# ==========================================
if __name__ == "__main__":
    codigo_fonte = """
    # 1. Aloca um vetor com 3 posicoes (Slots 0, 1 e 2)
    mine inventario[3];

    # 2. Atribui itens diretamente calculando os Offsets corretos
    inventario[0] = 64;  # Guarda terra
    inventario[1] = 12;  # Guarda ferro
    inventario[2] = 5;   # Guarda diamantes

    mostra("Vetor 'inventario' alocado na memoria e preenchido via indices!");
    """
    
    print("Iniciando mineração dos tokens...")
    tokens = analisar_lexico(codigo_fonte)
    
    print("Craftando executável x86...")
    codigo_asm = compilar_para_assembly(tokens)
    
    with open("saida.asm", "w") as f:
        f.write(codigo_asm)
        
    print("Sucesso! Compile para validar a manipulacao da Array.")