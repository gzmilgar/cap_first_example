@AbapCatalog.viewEnhancementCategory: [#NONE]
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Customer View'
@Metadata.ignorePropagatedAnnotations: true
@ObjectModel.usageType:{
    serviceQuality: #X,
    sizeCategory: #S,
    dataClass: #MIXED
}
define view entity ZI_GILGAR_T_CUST
  as select from zgilgar_t_cust as Cust
{
  key customer   as Customer,
      first_name as FirstName,
      last_name  as LastName
}
