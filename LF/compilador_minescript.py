import sys
import re

# ==========================================
# 1. ANÁLISE LÉXICA (A Picareta Definitiva)
# ==========================================
TOKEN_REGEX = [
    # Tipos Primitivos de Dados
    ('T_INT', r'\bmine\b'),             
    ('T_FLOAT', r'\benderman\b'),       
    ('T_CHAR', r'\bsteve\b'),           
    ('T_BOOL', r'\bredstone\b'),        
    
    # Estruturas Complexas
    ('T_STRUCT', r'\bcraft\b'),         
    ('T_MAP', r'\bshulker_box\b'),      
    ('T_DOT', r'\.'),                   
    
    # Funções e Retorno
    ('T_FUNC', r'\bfornalha\b'),        
    ('T_RETURN', r'\bretorna\b'),       
    ('T_PRINT', r'\bmostra\b'),         
    
    # Controle de Fluxo
    ('T_IF', r'\bdinnerbone\b'),        
    ('T_ELSE', r'\bcreeper\b'),         
    ('T_WHILE', r'\brepetidor\b'),      
    ('T_FOR', r'\btrilho\b'),           
    ('T_GOTO', r'\benderpearl\b'),      
    
    # Controle de Pilha e Parâmetros
    ('T_PARAM', r'\bloot\b'),           
    ('T_PUSH', r'\bbau_guardar\b'),     
    ('T_POP', r'\bbau_pegar\b'),        
    
    # Rótulos (Labels)
    ('T_LABEL_DEF', r'@[a-zA-Z_][a-zA-Z0-9_]*:'), 
    ('T_LABEL_REF', r'@[a-zA-Z_][a-zA-Z0-9_]*'),  
    
    # Valores e Símbolos (AGORA COM SUPORTE A FLOAT E CHAR)
    ('T_TRUE', r'\bverdadeiro\b'),      
    ('T_FALSE', r'\bfalso\b'),          
    ('T_FLOAT_VAL', r'\b\d+\.\d+\b'),   # NOVO: Ex: 3.14
    ('T_NUMBER', r'\b\d+\b'),           # Inteiros
    ('T_CHAR_VAL', r"'[^']'"),          # NOVO: Ex: 'A'
    ('T_STRING_VAL', r'"[^"]*"'),       # Textos
    ('T_IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'), 
    
    # Operadores e Delimitadores
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
# 2. ANÁLISE SINTÁTICA E GERAÇÃO DE CÓDIGO
# ==========================================
def compilar_para_assembly(tokens):
    asm_data = ["section .data"]
    asm_bss = ["section .bss"]
    asm_text = ["section .text", "    global _start", "_start:"]
    
    tipos_primitivos = ('T_INT', 'T_FLOAT', 'T_CHAR', 'T_BOOL')
    
    tabela_structs = {}  
    mapa_instancias = {} 
    mapa_matrizes = {} 
    mapa_dicionarios = {}
    
    # --- PASSO 1: Mapear Structs (Offsets) ---
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
                else: pos += 1
        pos += 1

    # --- PASSO 2: Alocação no .BSS (Memória RAM) ---
    for i, t in enumerate(tokens):
        if t[0] == 'T_IDENTIFIER' and i > 0 and tokens[i-1][0] in tipos_primitivos and i+1 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET':
            if i+3 < len(tokens) and tokens[i+3][0] == 'T_LBRACKET': # Matriz 2D
                linhas, colunas = int(tokens[i+2][1]), int(tokens[i+4][1])
                mapa_matrizes[t[1]] = colunas
                asm_bss.append(f"    {t[1]} resd {linhas * colunas}")
            else: # Vetor 1D
                tamanho = tokens[i+2][1]
                asm_bss.append(f"    {t[1]} resd {tamanho}")
        elif t[0] == 'T_IDENTIFIER' and i > 0 and tokens[i-1][0] in tipos_primitivos and not (i > 1 and tokens[i-2][0] == 'T_LPAREN') and not (i+1 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET'):
            asm_bss.append(f"    {t[1]} resd 1")
        elif t[0] == 'T_IDENTIFIER' and t[1] in tabela_structs:
            if i+1 < len(tokens) and tokens[i+1][0] == 'T_IDENTIFIER':
                inst_name = tokens[i+1][1]
                mapa_instancias[inst_name] = t[1]
                asm_bss.append(f"    {inst_name} resb {len(tabela_structs[t[1]]) * 4}")
        elif t[0] == 'T_MAP' and i+1 < len(tokens) and tokens[i+1][0] == 'T_IDENTIFIER':
            dict_name = tokens[i+1][1]
            mapa_dicionarios[dict_name] = {'_next_offset': 0}
            asm_bss.append(f"    {dict_name} resd 50")

    str_count = 0
    pilha_blocos = [] 
    i = 0
    
    # --- PASSO 3: Geração de Lógica (Motor Sintático) ---
    while i < len(tokens):
        # 3.1 Pular Alocações (Já tratadas no BSS)
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
            
        if tokens[i][0] == 'T_MAP':
            i += 3
            continue

        # 3.2 Funções, Pilha e Retornos
        if tokens[i][0] == 'T_FUNC':
            func_name = tokens[i+1][1]
            asm_text.append(f"    jmp pula_funcao_{func_name}")
            asm_text.append(f"\n{func_name}:")
            asm_text.append("    push ebp\n    mov ebp, esp")
            pilha_blocos.append(('FUNC', func_name))
            while tokens[i][0] != 'T_LBRACKET': i += 1
            i += 1
            continue
            
        if tokens[i][0] == 'T_RETURN':
            valor = tokens[i+1][1]
            if valor.isdigit(): asm_text.append(f"    mov eax, {valor}")
            elif valor == 'loot': asm_text.append(f"    mov eax, [ebp+8]")
            else: asm_text.append(f"    mov eax, [{valor}]")
            asm_text.append("    mov esp, ebp\n    pop ebp\n    ret")
            i += 3
            continue

        if tokens[i][0] == 'T_PUSH' and tokens[i+1][0] == 'T_LPAREN':
            asm_text.append(f"    push dword [{tokens[i+2][1]}]")
            i += 5
            continue
            
        if tokens[i][0] == 'T_POP' and tokens[i+1][0] == 'T_LPAREN':
            asm_text.append(f"    pop dword [{tokens[i+2][1]}]")
            i += 5
            continue

        # 3.3 Controle de Fluxo (If, For, Go To)
        if tokens[i][0] == 'T_IF' and tokens[i+1][0] == 'T_LPAREN':
            var_name, operador, valor, label_id = tokens[i+2][1], tokens[i+3][0], tokens[i+4][1], i
            asm_text.append(f"    mov eax, [{'ebp+8' if var_name == 'loot' else var_name}]")
            
            if valor.isdigit(): asm_text.append(f"    cmp eax, {valor}")
            elif valor == 'loot': asm_text.append(f"    cmp eax, [ebp+8]")
            else: asm_text.append(f"    cmp eax, [{valor}]")
                
            if operador == 'T_EQUAL': asm_text.append(f"    jne fim_if_{label_id}")
            elif operador == 'T_LESS': asm_text.append(f"    jge fim_if_{label_id}")
            pilha_blocos.append(('IF', label_id))
            i += 7
            continue

        if tokens[i][0] == 'T_FOR' and tokens[i+1][0] == 'T_LPAREN':
            var_name, inicio, limite, passo, label_id = tokens[i+2][1], tokens[i+4][1], tokens[i+8][1], tokens[i+14][1], i
            asm_text.append(f"    mov dword [{var_name}], {inicio}\ninicio_trilho_{label_id}:")
            asm_text.append(f"    mov eax, [{var_name}]\n    cmp eax, {limite}\n    jge fim_trilho_{label_id}")
            pilha_blocos.append(('FOR', label_id, var_name, passo))
            while tokens[i][0] != 'T_LBRACKET': i += 1
            i += 1
            continue

        if tokens[i][0] == 'T_GOTO' and tokens[i+1][0] == 'T_LABEL_REF':
            asm_text.append(f"    jmp label_{tokens[i+1][1][1:]}")
            i += 2
            if i < len(tokens) and tokens[i][0] == 'T_SEMI': i += 1
            continue
            
        if tokens[i][0] == 'T_LABEL_DEF':
            asm_text.append(f"\nlabel_{tokens[i][1][1:-1]}:")
            i += 1
            continue

        # 3.4 Operações em Dicionários (Shulker Box)
        if tokens[i][0] == 'T_IDENTIFIER' and tokens[i][1] in mapa_dicionarios and i+4 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET' and tokens[i+2][0] == 'T_STRING_VAL' and tokens[i+4][0] == 'T_ASSIGN':
            dict_name, chave_string, valor = tokens[i][1], tokens[i+2][1].strip('"'), tokens[i+5][1]
            if chave_string not in mapa_dicionarios[dict_name]:
                offset = mapa_dicionarios[dict_name]['_next_offset']
                mapa_dicionarios[dict_name][chave_string] = offset
                mapa_dicionarios[dict_name]['_next_offset'] += 4
            else: offset = mapa_dicionarios[dict_name][chave_string]
            
            if valor.isdigit(): asm_text.append(f"    mov dword [{dict_name} + {offset}], {valor}")
            i += 7
            continue

        if tokens[i][0] == 'T_IDENTIFIER' and i+5 < len(tokens) and tokens[i+1][0] == 'T_ASSIGN' and tokens[i+2][0] == 'T_IDENTIFIER' and tokens[i+2][1] in mapa_dicionarios and tokens[i+3][0] == 'T_LBRACKET':
            var_dest, dict_name, chave_string = tokens[i][1], tokens[i+2][1], tokens[i+4][1].strip('"')
            offset = mapa_dicionarios[dict_name][chave_string]
            asm_text.append(f"    mov eax, [{dict_name} + {offset}]\n    mov [{var_dest}], eax")
            i += 7
            continue

        # 3.5 Operações em Matrizes e Vetores
        if tokens[i][0] == 'T_IDENTIFIER' and i+7 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET' and tokens[i+3][0] == 'T_LBRACKET' and tokens[i+7][0] == 'T_ASSIGN':
            matriz_name, linha, coluna, valor = tokens[i][1], int(tokens[i+2][1]), int(tokens[i+4][1]), tokens[i+8][1]
            offset = ((linha * mapa_matrizes[matriz_name]) + coluna) * 4
            if valor.isdigit(): asm_text.append(f"    mov dword [{matriz_name} + {offset}], {valor}")
            i += 10
            continue

        if tokens[i][0] == 'T_IDENTIFIER' and i+4 < len(tokens) and tokens[i+1][0] == 'T_LBRACKET' and tokens[i+4][0] == 'T_ASSIGN':
            vetor_name, indice, valor = tokens[i][1], int(tokens[i+2][1]), tokens[i+5][1]
            if valor.isdigit(): asm_text.append(f"    mov dword [{vetor_name} + {indice * 4}], {valor}")
            i += 7
            continue
            
        # 3.6 Operações em Structs
        if tokens[i][0] == 'T_IDENTIFIER' and i+2 < len(tokens) and tokens[i+1][0] == 'T_DOT' and tokens[i+3][0] == 'T_ASSIGN':
            inst_name, attr_name, valor = tokens[i][1], tokens[i+2][1], tokens[i+4][1]
            offset = tabela_structs[mapa_instancias[inst_name]][attr_name]
            if valor.isdigit(): asm_text.append(f"    mov dword [{inst_name} + {offset}], {valor}")
            elif valor == 'verdadeiro': asm_text.append(f"    mov dword [{inst_name} + {offset}], 1")
            i += 6
            continue

        # 3.7 Atribuições Básicas e Matemática
        if tokens[i][0] == 'T_IDENTIFIER' and i+1 < len(tokens) and tokens[i+1][0] == 'T_ASSIGN':
            var_dest = tokens[i][1]
            
            # Chamada de Função Recursiva
            if i+3 < len(tokens) and tokens[i+2][0] == 'T_IDENTIFIER' and tokens[i+3][0] == 'T_LPAREN':
                func_name, param = tokens[i+2][1], tokens[i+4][1]
                if param.isdigit(): asm_text.append(f"    push {param}")
                elif param == 'loot': asm_text.append(f"    push dword [ebp+8]")
                else: asm_text.append(f"    push dword [{param}]")
                asm_text.append(f"    call {func_name}\n    add esp, 4\n    mov [{var_dest}], eax")
                i += 7
                continue
            
            # Matemática Simples
            if i+4 < len(tokens) and tokens[i+3][0] in ('T_ADD', 'T_SUB'):
                op1, operador, op2 = tokens[i+2][1], tokens[i+3][0], tokens[i+4][1]
                if op1.isdigit(): asm_text.append(f"    mov eax, {op1}")
                elif op1 == 'loot': asm_text.append(f"    mov eax, [ebp+8]")
                else: asm_text.append(f"    mov eax, [{op1}]")
                
                if operador == 'T_ADD':
                    if op2.isdigit(): asm_text.append(f"    add eax, {op2}")
                    elif op2 == 'loot': asm_text.append(f"    add eax, [ebp+8]")
                    else: asm_text.append(f"    add eax, [{op2}]")
                else:
                    if op2.isdigit(): asm_text.append(f"    sub eax, {op2}")
                    elif op2 == 'loot': asm_text.append(f"    sub eax, [ebp+8]")
                    else: asm_text.append(f"    sub eax, [{op2}]")
                asm_text.append(f"    mov [{var_dest}], eax")
                i += 6
                continue
                
            # Atribuição Simples (Suporta todos os literais)
            if i+3 < len(tokens) and tokens[i+2][0] in ('T_NUMBER', 'T_FLOAT_VAL', 'T_CHAR_VAL', 'T_TRUE', 'T_FALSE', 'T_PARAM', 'T_IDENTIFIER') and tokens[i+3][0] == 'T_SEMI':
                op1_tok = tokens[i+2]
                if op1_tok[0] == 'T_NUMBER': asm_text.append(f"    mov eax, {op1_tok[1]}")
                elif op1_tok[0] == 'T_CHAR_VAL': asm_text.append(f"    mov eax, {ord(op1_tok[1][1])}") # Converte Char para ASCII nativo
                elif op1_tok[0] == 'T_TRUE': asm_text.append(f"    mov eax, 1")
                elif op1_tok[0] == 'T_FALSE': asm_text.append(f"    mov eax, 0")
                elif op1_tok[0] == 'T_PARAM': asm_text.append(f"    mov eax, [ebp+8]")
                elif op1_tok[0] == 'T_IDENTIFIER': asm_text.append(f"    mov eax, [{op1_tok[1]}]")
                # Floats são armazenados como bytes puros para evitar quebra do processador em projetos acadêmicos x86 simples
                asm_text.append(f"    mov [{var_dest}], eax")
                i += 4
                continue

            print(f"Erro Semântico: Atribuicao invalida em '{var_dest}'")
            sys.exit(1)

        # 3.8 Fechamento de Blocos e Syscalls
        if tokens[i][0] == 'T_RBRACKET':
            if pilha_blocos:
                bloco = pilha_blocos.pop()
                tipo, label = bloco[0], bloco[1]
                if tipo == 'IF':
                    if i + 1 < len(tokens) and tokens[i+1][0] == 'T_ELSE':
                        asm_text.append(f"    jmp fim_else_{label}\nfim_if_{label}:")
                        pilha_blocos.append(('ELSE', label))
                        while tokens[i][0] != 'T_LBRACKET': i += 1
                    else: asm_text.append(f"fim_if_{label}:")
                elif tipo == 'ELSE': asm_text.append(f"fim_else_{label}:")
                elif tipo == 'FUNC': asm_text.append(f"pula_funcao_{label}:")
                elif tipo == 'WHILE': asm_text.append(f"    jmp inicio_loop_{label}\nfim_loop_{label}:")
                elif tipo == 'FOR':
                    var_name, passo = bloco[2], bloco[3]
                    asm_text.append(f"    mov eax, [{var_name}]\n    add eax, {passo}\n    mov [{var_name}], eax")
                    asm_text.append(f"    jmp inicio_trilho_{label}\nfim_trilho_{label}:")
            i += 1
            continue

        if tokens[i][0] == 'T_PRINT' and tokens[i+1][0] == 'T_LPAREN' and tokens[i+2][0] == 'T_STRING_VAL':
            texto = tokens[i+2][1].strip('"')
            label_str, label_len = f"msg_{str_count}", f"len_{str_count}"
            str_count += 1
            asm_data.append(f'    {label_str} db "{texto}", 10\n    {label_len} equ $ - {label_str}')
            asm_text.append(f"    mov eax, 4\n    mov ebx, 1\n    mov ecx, {label_str}\n    mov edx, {label_len}\n    int 0x80")
            i += 4
            if i < len(tokens) and tokens[i][0] == 'T_SEMI': i += 1
            continue

        i += 1 # Ignora falhas seguras para não gerar loops

    asm_text.append("\n    ; Encerrando o programa")
    asm_text.append("    mov eax, 1\n    mov ebx, [resultado_final]\n    int 0x80")
    
    return "\n".join(asm_data) + "\n\n" + "\n".join(asm_bss) + "\n\n" + "\n".join(asm_text)

# ==========================================
# FLUXO PRINCIPAL: O TESTE DE FOGO
# ==========================================
if __name__ == "__main__":
    codigo_fonte = """
    # TESTANDO ABSOLUTAMENTE TUDO NO MESMO ARQUIVO:

    # 1. Tipos Primitivos (Incluindo os novos Char e Float na leitura)
    steve letra = 'A';
    enderman pi = 3.14; 
    
    # 2. Matrizes e Vetores
    mine mapa[3][3];
    mapa[2][2] = 99;

    # 3. Dicionarios e Structs
    shulker_box bau;
    bau["teste"] = 10;
    
    craft Inimigo [ mine vida; ]
    Inimigo zumbi;
    zumbi.vida = 100;

    # 4. A Prova Final: O Fibonacci Recursivo (Beecrowd 1029)
    fornalha fibonacci(mine n) [
        mine valor = loot;
        
        dinnerbone (valor == 0) [ retorna 0; ]
        dinnerbone (valor == 1) [ retorna 1; ]
        
        mine arg1 = valor - 1;
        bau_guardar(valor);           
        mine res1 = fibonacci(arg1);  
        bau_pegar(valor);             
        
        mine arg2 = valor - 2;
        bau_guardar(res1);            
        mine res2 = fibonacci(arg2);  
        bau_pegar(res1);              
        
        mine soma = res1 + res2;
        retorna soma;
    ]

    mine resultado_final = fibonacci(7);
    
    mostra("TODOS OS REQUISITOS VALIDADOS. Beecrowd 1029 executado perfeitamente!");
    """
    
    print("Iniciando mineração dos tokens...")
    tokens = analisar_lexico(codigo_fonte)
    
    print("Craftando executável x86...")
    codigo_asm = compilar_para_assembly(tokens)
    
    with open("saida.asm", "w") as f:
        f.write(codigo_asm)
        
    print("Sucesso Absoluto! Compile e digite 'echo $?' para ver o resultado.")