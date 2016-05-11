"use strict";

let ImageController = function(container) {
  this.container_ = container;
  this.image_types_ = new Map();

  this.connect_();

  this.timer_ = setInterval((e) => this.onTick_(), 250);
};

ImageController.prototype.connect_ = function() {
  this.ws_ = new WebSocket('wss://' + location.host + '/ws/master', 'iconograph-master');
  this.ws_.addEventListener('message', (e) => this.onMessage_(JSON.parse(e.data)));
  this.ws_.addEventListener('close', (e) => this.onClose_());
};

ImageController.prototype.onClose_ = function() {
  setTimeout((e) => this.connect_(), 5000);
};

ImageController.prototype.onMessage_ = function(msg) {
  switch (msg['type']) {
    case 'image_types':
      return this.onImageTypes_(msg['data']);
    case 'report':
      return this.onReport_(msg['data']);
    case 'targets':
      return this.onTargets_(msg['data']);
  }
};

ImageController.prototype.onImageTypes_ = function(msg) {
  let image_types = new Set(msg['image_types']);
  for (let type of image_types) {
    if (!this.image_types_.has(type)) {
      this.addImageType_(type);
    }
  }
  for (let [type, value] of this.image_types_) {
    if (!image_types.has(type)) {
      this.removeImageType_(type);
    }
  };
};

ImageController.prototype.addImageType_ = function(type) {
  let value = {
    section: document.createElement('imageTypeSection'),
    instances: new Map(),
  };
  this.insertSorted_(this.container_, value.section, type);
  let headers = this.createNode_(value.section, 'headers');
  this.createNode_(headers, 'header', 'Hostname');
  this.createNode_(headers, 'header', 'Last report');
  this.createNode_(headers, 'header', 'Uptime');
  this.createNode_(headers, 'header', 'Current image');
  this.createNode_(headers, 'header', 'Current volume ID');
  this.createNode_(headers, 'header', 'Next image');
  this.createNode_(headers, 'header', 'Next volume ID');
  this.image_types_.set(type, value);
};

ImageController.prototype.removeImageType_ = function(type) {
  this.container_.removeChild(this.image_types_.get(type).section);
  this.image_types_.delete(type);
};

ImageController.prototype.onReport_ = function(msg) {
  let type = this.image_types_.get(msg['image_type']);
  if (!type.instances.has(msg['hostname'])) {
    this.addInstance_(type, msg['hostname']);
  }
  let instance = type.instances.get(msg['hostname']);
  instance.last_report_timestamp = Math.floor(Date.now() / 1000);
  instance.last_report.innerText = this.formatSeconds_(0);
  instance.uptime.innerText = this.formatSeconds_(msg['uptime_seconds']);
  instance.timestamp.innerText = msg['timestamp'];
  let volume_id_len = localStorage.getItem('volume_id_len') || Number.POSITIVE_INFINITY;
  instance.volume_id.innerText = msg['volume_id'].substring(0, volume_id_len);
  instance.next_timestamp.innerText = msg['next_timestamp'];
  instance.next_volume_id.innerText = msg['next_volume_id'].substring(0, volume_id_len);
};

ImageController.prototype.addInstance_ = function(type, hostname) {
  let value = {
    section: document.createElement('instanceSection'),
  };
  this.insertSorted_(type.section, value.section, hostname);
  this.createNode_(value.section, 'hostname', hostname);
  value.last_report = this.createNode_(value.section, 'lastReport');
  value.uptime = this.createNode_(value.section, 'uptime');
  value.timestamp = this.createNode_(value.section, 'timestamp');
  value.volume_id = this.createNode_(value.section, 'volumeID');
  value.next_timestamp = this.createNode_(value.section, 'timestamp');
  value.next_volume_id = this.createNode_(value.section, 'volumeID');
  value.reboot = this.createNode_(value.section, 'reboot', 'Reboot');

  value.volume_id.addEventListener(
      'click', (e) => this.onVolumeIDClick_(e.target.innerText));
  value.next_volume_id.addEventListener(
      'click', (e) => this.onVolumeIDClick_(e.target.innerText));
  value.reboot.addEventListener(
      'click', (e) => this.sendReboot_(hostname));

  type.instances.set(hostname, value);
};

ImageController.prototype.onTargets_ = function(msg) {
  let targets = new Set(msg['targets']);
  for (let [type, type_value] of this.image_types_) {
    for (let [instance, instance_value] of type_value.instances) {
      if (targets.has(instance)) {
        instance_value.section.classList.add('live');
      } else {
        instance_value.section.classList.remove('live');
      }
    }
  }
};

ImageController.prototype.onTick_ = function() {
  let now = Math.floor(Date.now() / 1000);
  for (let [type, type_value] of this.image_types_) {
    for (let [instance, instance_value] of type_value.instances) {
      instance_value.last_report.innerText =
          this.formatSeconds_(now - instance_value.last_report_timestamp);
    }
  }
};

ImageController.prototype.onVolumeIDClick_ = function(volume_id) {
  let base_url = localStorage.getItem('volume_id_url');
  if (!base_url) {
    return;
  }
  open(base_url.replace('VOLUMEID', volume_id));
};

ImageController.prototype.sendReboot_ = function(hostname) {
  this.ws_.send(JSON.stringify({
    'type': 'command',
    'target': hostname,
    'data': {
      'command': 'reboot',
    },
  }));
};

ImageController.prototype.insertSorted_ = function(parent, new_child, key) {
  let insert_before = null;
  for (var i = 0; i < parent.childNodes.length; i++) {
    let child = parent.childNodes[i];
    if (child.getAttribute('data-key') > key) {
      insert_before = child;
      break;
    }
  }

  new_child.setAttribute('data-key', key);
  parent.insertBefore(new_child, insert_before);
};

ImageController.prototype.createNode_ = function(parent, tag_name, text_content) {
  let node = document.createElement(tag_name);
  node.innerText = text_content || null;
  parent.appendChild(node);
  return node;
};

ImageController.TIERS_ = [
  [ 60 * 60 * 24 * 7, 'w' ],
  [ 60 * 60 * 24, 'd' ],
  [ 60 * 60, 'h' ],
  [ 60, 'm' ],
];

ImageController.prototype.formatSeconds_ = function(seconds) {
  for (let [threshold, suffix] of ImageController.TIERS_) {
    if (seconds > threshold) {
      return Math.floor(seconds / threshold) + suffix;
    }
  }
  return seconds + 's';
};


document.addEventListener('DOMContentLoaded', (e) => {
  new ImageController(document.getElementsByTagName('imageContainer')[0]);
});
