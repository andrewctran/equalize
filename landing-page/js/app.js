$(document).ready(function() {
  $('#particles').particleground({
    dotColor: '#263646',
    lineColor: '#263646',
    density: '5000',
    particleRadius: '2',
    lineWidth: '0.2'
  });
  $('.intro').css({
    'margin-top': -($('.intro').height() / 2)
  });
});