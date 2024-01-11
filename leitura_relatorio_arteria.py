from funcoes_arteria import search

search_xml = """<SearchReport id="11299" name="rel_precatorios_pre_analise">
  <DisplayFields>
    <DisplayField>27080</DisplayField>
    <DisplayField>27103</DisplayField>
    <DisplayField>27099</DisplayField>
    <DisplayField>27083</DisplayField>
    <DisplayField>27105</DisplayField>
    <DisplayField>27093</DisplayField>
    <DisplayField>27086</DisplayField>
    <DisplayField>27090</DisplayField>
    <DisplayField>27096</DisplayField>
    <DisplayField>27101</DisplayField>
    <DisplayField>27095</DisplayField>
    <DisplayField>27091</DisplayField>
    <DisplayField>27084</DisplayField>
    <DisplayField>27089</DisplayField>
  </DisplayFields>
  <PageSize>50050</PageSize>
  <IsResultLimitPercent>False</IsResultLimitPercent>
  <Criteria>
    <Keywords />
    <Filter>
      <OperatorLogic />
      <Conditions>
        <TextFilterCondition>
          <Field>27106</Field>
          <Operator>Contains</Operator>
          <Value />
        </TextFilterCondition>
      </Conditions>
    </Filter>
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
</SearchReport>"""

def get_dados_pagamentos_codigo_comprovantes(search_xml):
    dados = search(search_xml, page=1, quantidade=False)
    ids = []
    for i in range(len(dados)):
        print(dados[i])
        ids.append(dados[i]['ID de rastreamento'])
    return dados

get_dados_pagamentos_codigo_comprovantes(search_xml)