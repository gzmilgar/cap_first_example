@EndUserText.label: 'Header Test BO Projection View'
@AccessControl.authorizationCheck: #NOT_REQUIRED
@Search.searchable: true
@Metadata.allowExtensions: true
define root view entity ZC_GILGAR_T_HEADER
  as projection on Zi_GILGAR_T_HEADER as Header
{
      @Search.defaultSearchElement: true
  key Id,
      @Search.defaultSearchElement: true
      Customer,
      CreatedBy,
      CreatedAt,
      _Cust.first_name as CustFirstName,
      _Cust.last_name as CustLastName,
      /* Associations */
      _Cust,
      _Item : redirected to composition child ZC_GILGAR_T_ITEM
}
