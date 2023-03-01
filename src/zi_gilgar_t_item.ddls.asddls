@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Item View'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType:{
    serviceQuality: #X,
    sizeCategory: #S,
    dataClass: #MIXED
}
define view entity Zi_GILGAR_T_ITEM as select from zgilgar_t_item as Item
association to parent  Zi_GILGAR_T_HEADER as _Header on $projection.Id = _Header.Id
{
    key id as Id,
    key item_id as ItemId,
    value as Value,
    _Header
}
