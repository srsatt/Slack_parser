$(document).ready(function() {
      $( "div.project" ).mouseover(function() {
      $( this ).find( "div" ).show();
      $(this).css("background", "gray");
    })
    .mouseout(function() {
    $( this ).find( "div" ).hide();
      $(this).css("background", "white");
    });
        });
