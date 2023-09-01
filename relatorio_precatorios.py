from funcoes_arteria import search


search_xml = '''
<SearchReport id="11282" name="Rel_precatorio">
  <DisplayFields>
    <DisplayField>27080</DisplayField>
    <DisplayField>27099</DisplayField>
    <DisplayField>27103</DisplayField>
    <DisplayField>27089</DisplayField>
    <DisplayField>27083</DisplayField>
    <DisplayField>27084</DisplayField>
    <DisplayField>27088</DisplayField>
  </DisplayFields>
  <PageSize>50</PageSize>
  <IsResultLimitPercent>False</IsResultLimitPercent>
  <Criteria>
    <Keywords />
    <ModuleCriteria>
      <Module>599</Module>
      <IsKeywordModule>True</IsKeywordModule>
      <BuildoutRelationship>Union</BuildoutRelationship>
      <SortFields>
        <SortField>
          <Field>27080</Field>
          <SortType>Ascending</SortType>
        </SortField>
      </SortFields>
    </ModuleCriteria>
  </Criteria>
</SearchReport>
'''

def get_dados_pagamentos_codigo_comprovantes(search_xml):
    dados = search(search_xml, page=1, quantidade=False)
    ids = []
    for i in range(len(dados)):
        print(dados)
    return dados

get_dados_pagamentos_codigo_comprovantes(search_xml)