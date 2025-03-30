# PROCESSAMENTO DE MENSALIDADES

## Sistema de Armazenamento
- O sistema primeiro verifica se já processou as mensalidades anteriormente.
- Se já processou, usa os dados salvos para ser mais rápido.
- Se não, faz uma nova leitura completa da planilha de mensalidades.

## Análise da Planilha
- Lê cada página da planilha de mensalidades.
- Identifica automaticamente se é plano Apartamento ou Enfermaria.
- Verifica todos os meses do ano (janeiro a dezembro).
- Organiza os dados por família (titular e dependentes).

## Regras de Cálculo

### Para clientes da Câmara:
- O valor total é dividido entre os dependentes.
- O titular não recebe parte do valor.
- Cada dependente recebe proporcionalmente aos meses que utilizou o plano.

### Para demais clientes:
- O valor é dividido entre os 4 primeiros membros da família.
- Inclui o titular na divisão.
- Cada pessoa recebe conforme os meses que teve o plano ativo.

## Cálculo dos Valores
1. Pega o valor total anual da família.
2. Conta quantos meses cada pessoa usou o plano.
3. Divide o valor total pelo número total de meses.
4. Multiplica pelo número de meses que cada pessoa usou.

---

# BUSCA DE DADOS DE MENSALIDADES

## Localização dos Dados
- Busca todas as informações usando o CPF do titular.
- Organiza primeiro os dados do titular, depois dos dependentes.

## Verificação de Valores
- Confere se o total calculado bate com o valor anual esperado.
- Se houver diferença, ajusta automaticamente.
- Garante que ninguém receba valor negativo.

## Apresentação Final
- Mostra os valores em reais (R$).
- Organiza por nome de cada beneficiário.
- Apresenta os valores com duas casas decimais.

### Esta organização garante que:
- Cada família receba exatamente o valor correto.
- Os valores sejam distribuídos de forma justa.
- O sistema respeite as regras diferentes para clientes da Câmara.
- Todos os valores fechem com o total anual esperado.

---

# PROCESSAMENTO DE DESCONTOS

## Leitura dos Dados
- O sistema acessa a planilha "DESCONTOS.xlsx".
- Verifica todas as páginas da planilha.
- Foca nas colunas de Nome e Total de Descontos.
- Mantém um registro salvo para consultas rápidas.

## Organização dos Valores
- Agrupa todos os descontos por nome do beneficiário.
- Soma os valores quando há múltiplos descontos.
- Padroniza os nomes para evitar duplicidades.
- Arredonda valores para duas casas decimais.

## Armazenamento
- Mantém uma lista organizada de descontos.
- Permite consultas rápidas quando necessário.
- Economiza tempo em processamentos futuros.

---

# BUSCA DE DESCONTOS

## Processo de Busca
- Localiza beneficiários pelo CPF do titular.
- Verifica mensalidades associadas ao CPF.
- Busca descontos para cada membro da família.

## Cálculo dos Valores
- Soma todos os descontos encontrados.
- Considera todos os membros vinculados ao titular.
- Garante que nenhum desconto seja contado duas vezes.

## Validações
- Confirma se o nome está correto na base.
- Verifica se existem descontos registrados.
- Soma zero quando não há descontos.

## Resultado Final
- Retorna o valor total dos descontos.
- Mantém histórico das consultas.
- Permite rastreamento dos valores.

### Benefícios do Sistema:
- Precisão nos valores de desconto.
- Rapidez nas consultas.
- Confiabilidade nos dados.
- Facilidade de verificação.
- Histórico completo por beneficiário.

---

# PROCESSAMENTO DE DESPESAS

## Leitura dos Arquivos
- Sistema acessa a pasta `despesas_nova`.
- Lê todos os arquivos CSV de despesas.
- Foca em informações essenciais:
  - CPF do Responsável.
  - Nome do Beneficiário.
  - Valor do Serviço.

## Organização dos Dados
- Agrupa despesas por beneficiário.
- Soma todos os valores de serviços.
- Padroniza formatos de CPF.
- Mantém registro único por beneficiário.

## Sistema de Cache
- Salva processamento em arquivo `despesas_file.csv`.
- Otimiza consultas futuras.
- Reduz tempo de processamento.
- Mantém consistência dos dados.

---

# BUSCA DE DESPESAS

## Processo de Busca
- Localiza despesas por CPF e nome.
- Verifica todos os registros associados.
- Considera descontos relacionados.

## Distribuição de Valores
- Calcula diferença entre descontos e despesas.
- Distribui valores entre beneficiários quando necessário.
- Ajusta valores conforme regras específicas:
  - Se há descontos maiores que despesas.
  - Se há despesas sem descontos correspondentes.
  - Se há beneficiários sem registros.

## Ajustes Automáticos
- Distribui diferenças proporcionalmente.
- Trata casos de valores insuficientes.
- Ajusta registros individuais quando necessário.
- Garante que soma total esteja correta.

## Formatação Final
- Apresenta valores em formato monetário brasileiro.
- Organiza por nome do beneficiário.
- Inclui todos os valores relacionados.
- Mantém rastreabilidade dos dados.

### Benefícios do Sistema:
- Precisão nos valores processados.
- Distribuição equitativa de ajustes.
- Rastreamento completo de despesas.
- Integração com sistema de descontos.
- Rapidez nas consultas.
- Consistência nos dados.

---

# GERAÇÃO DE PDF - DETALHAMENTO:

## Cálculos de Valores e fluxo de construção do arquivo:

- Soma valores por beneficiário
- Formata com duas casas decimais
- Condicionais de Processamento
- Para cada beneficiário:
- Se existir nome: inclui na lista
- Se valor ausente: usa "R$ 0,00"
- Se dados incompletos: marca como "N/A"
- Ajustes de Totais
- Verifica valores vazios antes da conversão
- Soma apenas valores válidos
- Formata total em moeda brasileira
- Adiciona totais de descontos

# GERAÇÃO DE DMED - DETALHAMENTO:

## Regras de Processamento

### Para cada titular:

- Se CPF válido: processa família
- Se tem dependentes: ordena por CPF
- Se tem despesas: soma com mensalidades
- Cálculos por Beneficiário

### Titular:

- Valor mensalidade + valor despesas
- Formatação em centavos (9 dígitos)
- Valor zero se só dependentes

### Dependentes:

- Valor individual calculado
- Soma de despesas próprias
- Formatação específica DMED
- Condicionais de Registro

### Se é Câmara:
- Titular sem valor
- Dependentes recebem distribuição

### Se é normal:
- Titular participa da divisão
- Limita a 4 beneficiários
- Validações de Valores

### Se existem valores:
- Distribui entre beneficiários
- Ajusta diferenças
- Garante soma correta

### Se não há valores:
- Registra zerado
- Mantém estrutura padrão

Formatação Final
Valores em centavos
CPFs com 11 dígitos
Nomes padronizados
Códigos de relação específicos
O sistema mantém consistência matemática e segue rigorosamente as regras da Receita Federal para declaração DMED.

O sistema garante que todas as despesas sejam corretamente processadas e distribuídas, mantendo a integridade dos dados e a transparência necessária para o negócio.