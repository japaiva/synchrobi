import csv
from core.models import ContaContabil, ContaContabilExterna
from datetime import datetime

csv_file = '/tmp/inserir_contas_externas.csv'

print(f'\n{"="*80}')
print('IMPORTAÇÃO DE CÓDIGOS EXTERNOS DE CONTAS CONTÁBEIS')
print(f'{"="*80}\n')
print(f'Arquivo: {csv_file}')
print(f'Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}\n')

sucessos = 0
erros = 0
pulos = 0
erros_lista = []

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    linhas = list(reader)
    total = len(linhas)

    print(f'Total de registros a importar: {total}\n')
    print('-' * 80)

    for idx, row in enumerate(linhas, 1):
        codigo_externo = row['codigo_externo'].strip()
        nome_externo = row['nome_externo'].strip()
        conta_codigo = row['conta_contabil'].strip()
        sistema_origem = row['sistema_origem'].strip() or 'ERP'

        try:
            # Verificar se já existe
            if ContaContabilExterna.objects.filter(codigo_externo=codigo_externo).exists():
                print(f'{idx:3}/{total} ⏭️  PULADO: {codigo_externo:15} | Já existe')
                pulos += 1
                continue

            # Buscar conta contábil
            try:
                conta = ContaContabil.objects.get(codigo=conta_codigo)
            except ContaContabil.DoesNotExist:
                msg = f'Conta contábil não encontrada: {conta_codigo}'
                print(f'{idx:3}/{total} ❌ ERRO: {codigo_externo:15} | {msg}')
                erros += 1
                erros_lista.append({'linha': idx, 'codigo': codigo_externo, 'erro': msg})
                continue

            # Criar código externo
            conta_externa = ContaContabilExterna.objects.create(
                codigo_externo=codigo_externo,
                nome_externo=nome_externo,
                sistema_origem=sistema_origem,
                conta_contabil=conta,
                ativa=True,
                observacoes='Importado do cadastro completo Marie'
            )

            print(f'{idx:3}/{total} ✓ OK: {codigo_externo:15} | Conta: {conta_codigo:15} | {nome_externo[:40]}')
            sucessos += 1

        except Exception as e:
            msg = str(e)
            print(f'{idx:3}/{total} ❌ ERRO: {codigo_externo:15} | {msg}')
            erros += 1
            erros_lista.append({'linha': idx, 'codigo': codigo_externo, 'erro': msg})

# Resumo
print('\n' + '='*80)
print('RESUMO DA IMPORTAÇÃO')
print('='*80)
print(f'Total de registros processados: {total}')
print(f'✓ Sucessos:  {sucessos:3} ({sucessos*100//total if total > 0 else 0}%)')
print(f'⏭  Pulados:   {pulos:3} ({pulos*100//total if total > 0 else 0}%)')
print(f'❌ Erros:     {erros:3} ({erros*100//total if total > 0 else 0}%)')

if erros_lista:
    print(f'\n{"="*80}')
    print('DETALHES DOS ERROS')
    print('='*80)
    for erro_info in erros_lista[:20]:
        print(f'Linha {erro_info["linha"]}: {erro_info["codigo"]} - {erro_info["erro"]}')
    if len(erros_lista) > 20:
        print(f'\n... e mais {len(erros_lista) - 20} erros')

print(f'\n{"="*80}\n')
