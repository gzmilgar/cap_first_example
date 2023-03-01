@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Header View'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType:{
    serviceQuality: #X,
    sizeCategory: #S,
    dataClass: #MIXED
}
define root view entity Zi_GILGAR_T_HEADER
  as select from zgilgar_t_header as Header
  composition [1..*] of Zi_GILGAR_T_ITEM as _Item
  association [1..1] to zgilgar_t_cust   as _Cust on $projection.Customer = _Cust.customer
{
  key id         as Id,
      customer   as Customer,
      @Semantics.user.createdBy: true
      created_by as CreatedBy,
      @Semantics.systemDateTime.createdAt: true
      created_at as CreatedAt,
      _Item,
      _Cust
}
