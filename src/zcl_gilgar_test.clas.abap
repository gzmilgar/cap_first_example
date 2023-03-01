CLASS zcl_gilgar_test DEFINITION
  PUBLIC
  FINAL
  CREATE PUBLIC .

  PUBLIC SECTION.
    INTERFACES if_oo_adt_classrun.
  PROTECTED SECTION.
  PRIVATE SECTION.
ENDCLASS.

CLASS zcl_gilgar_test IMPLEMENTATION.

  METHOD if_oo_adt_classrun~main.

    DATA: header TYPE TABLE OF zgilgar_t_header,
          item   TYPE TABLE OF zgilgar_t_item,
          cust   TYPE TABLE OF zgilgar_t_cust.

    header = VALUE #(
      ( id = '1' customer = 'SAP')
      ( id = '2' customer = 'SAP' )
      ( id = '3' customer = 'CLOUD' )
    ).
    DELETE FROM zgilgar_t_header.
    INSERT zgilgar_t_header FROM TABLE @header.

   item = VALUE #(
      ( id = '1' item_id = '001' value = 'TEST1' )
      ( id = '1' item_id = '002' value = '12345' )
      ( id = '1' item_id = '003' value = '12345' )
      ( id = '2' item_id = '001' value = 'TEST2' )
      ( id = '3' item_id = '001' value = 'TEST3' )
    ).
    DELETE FROM zgilgar_t_item.
    INSERT zgilgar_t_item FROM TABLE @item.

    cust = VALUE #(
      ( customer = 'SAP' first_name = 'SAP_first_name' last_name = 'SAP_last_name'  )
      ( customer = 'CLOUD' first_name = 'CLOUD_first_name' last_name = 'CLOUD_last_name'  )
    ).
    DELETE FROM zgilgar_t_cust.
    INSERT zgilgar_t_cust FROM TABLE @cust.



    out->write( |{ sy-dbcnt } test successfully!| ).
    COMMIT WORK AND WAIT.
  ENDMETHOD.

ENDCLASS.
