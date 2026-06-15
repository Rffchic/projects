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
    ('T_FOR', r'\btrilho\b'),           # NOVO: A palavra reservada para o For Loop
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
    mapa_matrizes = {} # NOVO: Guarda o limite de colunas para fazer a matemática 2D
    
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

    # PASSO 2: Alocação Inteligente no .BSS
    for i, t in enumerate(tokens):
        # NOVO: Aloca Matrizes 2D ou Vetores 1D
        if t[0] == 'T_IDENTIFIER' and i > 0 and tokens[i-1][0] in tipos_primitivos and i+1 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET':
            if i+3 < len(tokens) and tokens[i+3][0] == 'T_LBRACKET': 
                # É uma Matriz 2D! (ex: mine mapa[2][2])
                linhas = int(tokens[i+2][1])
                colunas = int(tokens[i+4][1])
                mapa_matrizes[t[1]] = colunas
                asm_bss.append(f"    {t[1]} resd {linhas * colunas} ; Matriz {linhas}x{colunas}")
            else:
                # É um Vetor 1D! (ex: mine inventario[5])
                tamanho = tokens[i+2][1]
                asm_bss.append(f"    {t[1]} resd {tamanho} ; Vetor 1D")
            
        elif t[0] == 'T_IDENTIFIER' and i > 0 and tokens[i-1][0] in tipos_primitivos and not (i > 1 and tokens[i-2][0] == 'T_LPAREN') and not (i+1 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET'):
            asm_bss.append(f"    {t[1]} resd 1")
            
        elif t[0] == 'T_IDENTIFIER' and t[1] in tabela_structs:
            if i+1 < len(tokens) and tokens[i+1][0] == 'T_IDENTIFIER':
                inst_name = tokens[i+1][1]
                mapa_instancias[inst_name] = t[1]
                tamanho_total = len(tabela_structs[t[1]]) * 4
                asm_bss.append(f"    {inst_name} resb {tamanho_total}")

    str_count = 0
    pilha_blocos = [] 
    i = 0
    
    # PASSO 3: Geração de Lógica
    while i < len(tokens):
        if tokens[i][0] in tipos_primitivos:
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

        # NOVO: Atribuição do Laço For (trilho)
        # Sintaxe esperada: trilho ( i = 0 ; i < 3 ; i = i + 1 ) [
        if tokens[i][0] == 'T_FOR' and tokens[i+1][0] == 'T_LPAREN':
            var_name = tokens[i+2][1]
            inicio = tokens[i+4][1]
            limite = tokens[i+8][1]
            passo = tokens[i+14][1]
            label_id = i
            
            asm_text.append(f"    ; trilho: {var_name} de {inicio} ate {limite} (passo {passo})")
            asm_text.append(f"    mov dword [{var_name}], {inicio}") # Inicializa
            asm_text.append(f"inicio_trilho_{label_id}:")
            asm_text.append(f"    mov eax, [{var_name}]")
            asm_text.append(f"    cmp eax, {limite}")
            asm_text.append(f"    jge fim_trilho_{label_id}") # Sai se chegou no limite
            
            # Guardamos na pilha as informações para injetar o incremento lá no colchete ']'
            pilha_blocos.append(('FOR', label_id, var_name, passo))
            
            while tokens[i][0] != 'T_LBRACKET': i += 1
            i += 1
            continue

        # NOVO: Atribuição em Matriz 2D (ex: mapa[1][1] = 99;)
        if tokens[i][0] == 'T_IDENTIFIER' and i+7 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET' and tokens[i+3][0] == 'T_LBRACKET' and tokens[i+7][0] == 'T_ASSIGN':
            matriz_name = tokens[i][1]
            linha = int(tokens[i+2][1])
            coluna = int(tokens[i+4][1])
            valor = tokens[i+8][1]
            
            # A Matemática da Matriz Linear
            colunas_total = mapa_matrizes[matriz_name]
            offset = ((linha * colunas_total) + coluna) * 4
            
            asm_text.append(f"    ; {matriz_name}[{linha}][{coluna}] = {valor}")
            if valor.isdigit():
                asm_text.append(f"    mov dword [{matriz_name} + {offset}], {valor}")
            i += 10
            continue

        # Atribuição em Vetor 1D
        if tokens[i][0] == 'T_IDENTIFIER' and i+4 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET' and tokens[i+4][0] == 'T_ASSIGN':
            vetor_name = tokens[i][1]
            indice = int(tokens[i+2][1])
            valor = tokens[i+5][1]
            offset = indice * 4
            
            asm_text.append(f"    ; {vetor_name}[{indice}] = {valor}")
            if valor.isdigit():
                asm_text.append(f"    mov dword [{vetor_name} + {offset}], {valor}")
            i += 7
            continue

        # Atribuição Primitiva ou Matemática Simples
        if tokens[i][0] == 'T_IDENTIFIER' and i+1 < len(tokens) and tokens[i+1][0] == 'T_ASSIGN':
            var_dest = tokens[i][1]
            
            # Matemática (ex: x = y + z;)
            if i+4 < len(tokens) and tokens[i+3][0] in ('T_ADD', 'T_SUB'):
                op1 = tokens[i+2][1]
                operador = tokens[i+3][0]
                op2 = tokens[i+4][1]
                
                asm_text.append(f"    ; {var_dest} = {op1} {'+' if operador == 'T_ADD' else '-'} {op2}")
                if op1.isdigit(): asm_text.append(f"    mov eax, {op1}")
                else: asm_text.append(f"    mov eax, [{op1}]")
                
                if operador == 'T_ADD':
                    if op2.isdigit(): asm_text.append(f"    add eax, {op2}")
                    else: asm_text.append(f"    add eax, [{op2}]")
                else:
                    if op2.isdigit(): asm_text.append(f"    sub eax, {op2}")
                    else: asm_text.append(f"    sub eax, [{op2}]")
                
                asm_text.append(f"    mov [{var_dest}], eax")
                i += 6
                continue

            # Atribuição Direta (ex: x = 10;)
            if i+3 < len(tokens) and tokens[i+2][0] in ('T_NUMBER', 'T_TRUE', 'T_FALSE') and tokens[i+3][0] == 'T_SEMI':
                op1 = tokens[i+2][1]
                asm_text.append(f"    ; {var_dest} = {op1}")
                if op1.isdigit(): asm_text.append(f"    mov eax, {op1}")
                elif op1 == 'verdadeiro': asm_text.append(f"    mov eax, 1")
                elif op1 == 'falso': asm_text.append(f"    mov eax, 0")
                asm_text.append(f"    mov [{var_dest}], eax")
                i += 4
                continue

        # Fechamento de Blocos ']' - Agora com suporte ao FOR
        elif tokens[i][0] == 'T_RBRACKET':
            if pilha_blocos:
                bloco = pilha_blocos.pop()
                tipo = bloco[0]
                
                if tipo == 'WHILE':
                    label = bloco[1]
                    asm_text.append(f"    jmp inicio_loop_{label}")
                    asm_text.append(f"fim_loop_{label}:")
                    
                # NOVO: Injetando o incremento do trilho antes de voltar
                elif tipo == 'FOR':
                    label = bloco[1]
                    var_name = bloco[2]
                    passo = bloco[3]
                    asm_text.append(f"    ; Incremento do trilho")
                    asm_text.append(f"    mov eax, [{var_name}]")
                    asm_text.append(f"    add eax, {passo}")
                    asm_text.append(f"    mov [{var_name}], eax")
                    asm_text.append(f"    jmp inicio_trilho_{label}")
                    asm_text.append(f"fim_trilho_{label}:")
                    
                elif tipo == 'IF':
                    label = bloco[1]
                    if i + 1 < len(tokens) and tokens[i+1][0] == 'T_ELSE':
                        asm_text.append(f"    jmp fim_else_{label}")
                        asm_text.append(f"fim_if_{label}:")
                        pilha_blocos.append(('ELSE', label))
                        while tokens[i][0] != 'T_LBRACKET': i += 1
                    else:
                        asm_text.append(f"fim_if_{label}:")
                elif tipo == 'ELSE':
                    asm_text.append(f"fim_else_{bloco[1]}:")
                elif tipo == 'FUNC':
                    asm_text.append(f"pula_funcao_{bloco[1]}:")
            i += 1

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

    # Finalização do programa
    asm_text.append("\n    ; Encerrando o programa")
    asm_text.append("    mov eax, 1")
    asm_text.append("    mov ebx, [meu_contador]") # O Exit Code devolve o valor de 'meu_contador' para provar o For!
    asm_text.append("    int 0x80")
    
    return "\n".join(asm_data) + "\n\n" + "\n".join(asm_bss) + "\n\n" + "\n".join(asm_text)

# ==========================================
# FLUXO PRINCIPAL (Testando For e Matrizes)
# ==========================================
if __name__ == "__main__":
    codigo_fonte = """
    # 1. Testando a Matemática de Matriz 2D
    mine mapa[3][3];
    mapa[2][2] = 99;  # Calculado como Offset 32 (Linha 2 * 3 Colunas + 2) * 4 bytes

    # 2. Testando o laco de repeticao FOR (trilho)
    mine i;
    mine meu_contador = 0;
    
    trilho (i = 0; i < 5; i = i + 1) [
        meu_contador = meu_contador + 2;
    ]

    # No final do trilho, meu_contador deve ser igual a 10 (5 vezes * 2)
    mostra("Motor do Trilho e Offsets de Matrizes injetados com sucesso!");
    """
    
    print("Iniciando mineração dos tokens...")
    tokens = analisar_lexico(codigo_fonte)
    
    print("Craftando executável x86...")
    codigo_asm = compilar_para_assembly(tokens)
    
    with open("saida.asm", "w") as f:
        f.write(codigo_asm)
        
    print("Sucesso! Compile e digite 'echo $?' para ver o resultado do FOR.")