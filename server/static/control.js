"use strict";

document.addEventListener('DOMContentLoaded', (e) => {
  let ws = new WebSocket('wss://' + location.host + '/ws/master', 'iconograph-master');
  ws.addEventListener('message', (e) => {
    let parsed = JSON.parse(e.data);
    console.log(parsed);
  });
});
