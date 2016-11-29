"use strict";

let ImageController = function(container) {
  this.container_ = container;
  this.overlay_ = this.createNode_(this.container_, 'overlay');
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
  switch (msg.type) {
    case 'image_types':
      return this.onImageTypes_(msg.data);
    case 'new_manifest':
      return this.onNewManifest_(msg.data);
    case 'report':
      return this.onReport_(msg.data);
    case 'targets':
      return this.onTargets_(msg.data);
  }
};

ImageController.prototype.onImageTypes_ = function(msg) {
  let image_types = new Set(msg.image_types);
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

ImageController.prototype.addImageType_ = function(name) {
  let type = {
    name: name,
    section: document.createElement('instances'),
    instances: new Map(),
  };
  this.insertSorted_(this.container_, type.section, name);
  let headers = this.createNode_(type.section, 'headers');
  this.createNode_(headers, 'header', 'Hostname');
  this.createNode_(headers, 'header', 'Last report');
  this.createNode_(headers, 'header', 'Uptime');
  this.createNode_(headers, 'header', 'Current image');
  this.createNode_(headers, 'header', 'Current volume ID');
  this.createNode_(headers, 'header', 'Next image');
  this.createNode_(headers, 'header', 'Next volume ID');
  this.createNode_(headers, 'header', 'Status');

  type.version_section = this.createNode_(this.overlay_, 'versions');
  type.version_section.setAttribute('data-key', name);
  type.version_hostname = this.createNode_(type.version_section, 'hostnameLabel');
  let close = this.createNode_(type.version_section, 'close', '✗');
  close.addEventListener(
      'click', (e) => type.version_section.classList.remove('live'));

  headers = this.createNode_(type.version_section, 'headers');
  this.createNode_(headers, 'header', 'Image');
  this.createNode_(headers, 'header', 'Volume ID');
  type.versions = this.createNode_(type.version_section, 'versionList');

  this.image_types_.set(name, type);

  this.fetchManifest_(type);
};

ImageController.prototype.removeImageType_ = function(type) {
  this.container_.removeChild(type.section);
  this.image_types_.delete(type.name);
};

ImageController.prototype.onNewManifest_ = function(msg) {
  this.fetchManifest_(this.image_types_.get(msg.image_type));
};

ImageController.prototype.fetchManifest_ = function(type) {
  let xhr = new XMLHttpRequest();
  xhr.addEventListener('load', (e) => this.onFetchManifest_(type, xhr.response));
  xhr.responseType = 'json';
  xhr.open('GET', 'https://' + location.host + '/image/' + type.name + '/manifest.json');
  xhr.send();
};

ImageController.prototype.onFetchManifest_ = function(type, wrapper) {
  let manifest = JSON.parse(wrapper.inner);
  let volume_id_len = localStorage.getItem('volume_id_len') || Number.POSITIVE_INFINITY;
  type.versions.innerHTML = '';
  for (let image of manifest.images) {
    image.volume_id = image.volume_id || '';
    let version = this.createNode_(type.versions, 'version');
    this.createNode_(version, 'timestamp', image.timestamp);
    let volume_id =
        this.createNode_(version, 'volumeID', image.volume_id.substring(0, volume_id_len));
    volume_id.addEventListener(
        'click', (e) => this.onVolumeIDClick_(e.target.innerText));

    let select = this.createNode_(version, 'command', 'Select');
    select.addEventListener(
        'click', (e) => {
            this.sendReboot_(type.version_hostname.innerText, image.timestamp);
            type.version_section.classList.remove('live');
        });
  }
};

ImageController.prototype.onReport_ = function(msg) {
  let type = this.image_types_.get(msg.image_type);
  if (!type.instances.has(msg.hostname)) {
    this.addInstance_(type, msg.hostname);
  }
  let instance = type.instances.get(msg.hostname);
  instance.last_report_timestamp = Math.floor(Date.now() / 1000);
  instance.last_report.innerText = this.formatSeconds_(0);
  instance.uptime.innerText = this.formatSeconds_(msg.uptime_seconds);
  instance.timestamp.innerText = msg.timestamp;
  let volume_id_len = localStorage.getItem('volume_id_len') || Number.POSITIVE_INFINITY;
  msg.volume_id = msg.volume_id || '';
  instance.volume_id.innerText = msg.volume_id.substring(0, volume_id_len);
  instance.next_timestamp.innerText = msg.next_timestamp;
  msg.next_volume_id = msg.next_volume_id || '';
  instance.next_volume_id.innerText = msg.next_volume_id.substring(0, volume_id_len);
  msg.status = msg.status || '';
  instance.status.innerText = msg.status;
};

ImageController.prototype.addInstance_ = function(type, hostname) {
  let instance = {
    section: document.createElement('instance'),
  };
  this.insertSorted_(type.section, instance.section, hostname);
  this.createNode_(instance.section, 'hostname', hostname);
  instance.last_report = this.createNode_(instance.section, 'lastReport');
  instance.uptime = this.createNode_(instance.section, 'uptime');
  instance.timestamp = this.createNode_(instance.section, 'timestamp');
  instance.volume_id = this.createNode_(instance.section, 'volumeID');
  instance.next_timestamp = this.createNode_(instance.section, 'timestamp');
  instance.next_volume_id = this.createNode_(instance.section, 'volumeID');
  instance.status = this.createNode_(instance.section, 'status');
  instance.reboot = this.createNode_(instance.section, 'reboot', 'Reboot');
  instance.select = this.createNode_(instance.section, 'reboot', 'Select');

  instance.volume_id.addEventListener(
      'click', (e) => this.onVolumeIDClick_(e.target.innerText));
  instance.next_volume_id.addEventListener(
      'click', (e) => this.onVolumeIDClick_(e.target.innerText));
  instance.reboot.addEventListener(
      'click', (e) => this.sendReboot_(hostname));
  instance.select.addEventListener(
      'click', (e) => this.onSelectClick_(type, hostname));

  type.instances.set(hostname, instance);
};

ImageController.prototype.onTargets_ = function(msg) {
  let targets = new Set(msg.targets);
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
      let stale = now - instance_value.last_report_timestamp;
      instance_value.last_report.innerText = this.formatSeconds_(stale);
      if (stale < 15) {
        instance_value.section.classList.remove('stale');
      } else {
        instance_value.section.classList.add('stale');
      }
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

ImageController.prototype.onSelectClick_ = function(type, hostname) {
  type.version_hostname.innerText = hostname;
  type.version_section.classList.add('live');
};

ImageController.prototype.sendReboot_ = function(hostname, opt_timestamp) {
  let command = {
    'type': 'command',
    'target': hostname,
    'data': {
      'command': 'reboot',
    },
  };
  if (opt_timestamp) {
    command.data.timestamp = opt_timestamp;
  }
  this.ws_.send(JSON.stringify(command));
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
  new ImageController(document.getElementsByTagName('container')[0]);
});
