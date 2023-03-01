@EndUserText.label: 'Item Test BO Projection View'
@AccessControl.authorizationCheck: #NOT_REQUIRED
@Search.searchable: true
@Metadata.allowExtensions: true
define view entity ZC_GILGAR_T_ITEM
  as projection on Zi_GILGAR_T_ITEM as Item
{
      @Search.defaultSearchElement: true
  key Id,
      @Search.defaultSearchElement: true
  key ItemId,
      Value,
      /* Associations */
      _Header : redirected to parent ZC_GILGAR_T_HEADER
}
