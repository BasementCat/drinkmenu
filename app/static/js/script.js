(function() {
    class SortableItem {
        constructor(parent, order, ele, handle, name_sel) {
            this.parent = parent;
            this.order = order;
            this.ele = ele;
            this.handle = handle ? this.ele.querySelector(handle) : null;
            this.dragtarget = null;
            this.name = null;
            if (name_sel) {
                let name_ele = this.ele.querySelector(name_sel);
                if (name_ele) {
                    this.name = name_ele.innerText;
                }
            }

            this.ele.draggable = true;

            if (this.handle) this.handle.addEventListener('mousedown', this.handle_target_mouseDown.bind(this));
            this.ele.addEventListener('dragstart', this.handle_dragStart.bind(this));
            this.ele.addEventListener('drag', this.handle_drag.bind(this));
            this.ele.addEventListener('dragover', this.parent.handle_dragOver.bind(this.parent));
            this.ele.addEventListener('dragend', this.handle_dragEnd.bind(this));
            this.ele.addEventListener('drop', this.handle_drop.bind(this));
        }

        get midpoint() {
            return this.pos.y + (this.pos.height / 2);
        }

        get pos() {
            return this.ele.getBoundingClientRect();
        }

        get _next_sibling() {
            var next = this.ele;
            while (true) {
                next = next.nextSibling;
                if (!next) return;
                let c = this.parent.find_child(next);
                if (c) return c;
            }
        }
        get _previous_sibling() {
            var previous = this.ele;
            while (true) {
                previous = previous.previousSibling;
                if (!previous) return;
                let c = this.parent.find_child(previous);
                if (c) return c;
            }
        }

        move_next_to(other_item, where) {
            if (where === 'above') {
                if (Object.is(other_item._previous_sibling, this)) return;
                other_item.ele.parentNode.insertBefore(this.ele, other_item.ele);
            } else if (where === 'below') {
                if (Object.is(other_item._next_sibling, this)) return;
                if (other_item.ele.nextSibling) {
                    other_item.ele.parentNode.insertBefore(this.ele, other_item.ele.nextSibling);
                } else {
                    other_item.ele.parentNode.insertBefore(this.ele);
                }
            }
            console.log("Move %o %s %o", this.name, where, other_item.name);
            this.parent._reorder(this, other_item, where);
        }

        handle_target_mouseDown(event) {
            // console.log("Set dragtarget to %o", event.target);
            this.dragtarget = event.target;
        }

        handle_dragStart(event) {
            // console.log("handle is %o, dragtarget is %o, handle contains dragtarget is %s", this.handle, this.dragtarget, this.handle.contains(this.dragtarget));
            if (this.handle && !this.handle.contains(this.dragtarget)) {
                event.preventDefault();
                return;
            }
            this.ele.style.transform = 'translateX(-9999px)';
        }

        handle_drag(event) {
            if (!this.parent.dragged_over || Object.is(this.parent.dragged_over, this)) return;
            if (event.y < this.parent.dragged_over.midpoint)
                this.move_next_to(this.parent.dragged_over, 'above');
            else
                this.move_next_to(this.parent.dragged_over, 'below');
        }

        handle_dragEnd(event) {
            this.ele.style.transform = 'unset';
        }

        handle_drop(event) {
            this.parent._trigger('sorted');
        }
    }

    class Sortable {
        constructor(ele, draggable, handle, name_sel) {
            this.container = ele;
            var i = 0;
            this.children = Array.prototype.slice.call(draggable ? this.container.querySelectorAll(draggable) : this.container.childNodes).map((c) => new SortableItem(this, i++, c, handle, name_sel));
            this.dragged_over = null;
            this.callbacks = {};
        }

        find_child(target) {
            if (!this.container.contains(target)) return false;
            for (var i = 0; i < this.children.length; i++) {
                if (this.children[i].ele.contains(target)) return this.children[i];
            }
            return false;
        }

        handle_dragOver(event) {
            this.dragged_over = this.find_child(event.target);
            if (this.dragged_over) event.preventDefault();
        }

        _reorder(dragged, over, where) {
            var found_over = false;
            for (var i = 0; i < this.children.length; i++) {
                if (found_over) {
                    if (Object.is(this.children[i], dragged)) continue;
                    this.children[i].order++;
                } else {
                    if (Object.is(this.children[i], over)) {
                        found_over = true;
                        if (where === 'above') {
                            // dragged element gets order of over, over and later get ++
                            dragged.order = over.order;
                            over.order++;
                        } else if (where === 'below') {
                            // dragged element gets order of over + 1 and later get ++
                            dragged.order = over.order + 1;
                        } else {
                            // If someone passed in the wrong shit, just bail
                            return;
                        }
                    }
                }
            }
        }

        on(event, callback) {
            this.callbacks[event] = this.callbacks[event] || [];
            this.callbacks[event].push(callback);
            return this;
        }

        _trigger(event) {
            (this.callbacks[event] || {}).forEach(function(cb) {
                cb(event, this);
            }.bind(this));
        }
    }
    document.querySelectorAll('[data-sortable="true"]').forEach(function(container) {
        new Sortable(container, 'tr', '.drag-handle', 'td:nth-child(2)')
            .on('sorted', function(ev, sb) {
                let order_by_id = {};
                sb.children.forEach((c) => order_by_id[parseInt(c.ele.getAttribute('data-id'))] = c.order);

                let req = new XMLHttpRequest();
                req.open('POST', '/api/admin/reorder/' + sb.container.getAttribute('data-sortable-type'));
                req.setRequestHeader('Content-Type', 'application/json')
                req.send(JSON.stringify(order_by_id));
            });
    });


    window.enable_autorefresh = function(delay) {
        delay = delay || 15000;

        let timeout = null, bar = null, bar_interval = null;

        let install_bar = function() {
            let container = document.createElement('div');
            container.classList.add('progress');
            bar = document.createElement('div');
            bar.classList.add('progress-bar');
            bar.classList.add('refresh-bar');
            bar.setAttribute('role', 'progressbar');
            bar.style.width = '100%';

            bar.style.animationDuration = delay + 'ms';

            container.appendChild(bar);
            document.querySelector('body>.container').prepend(container);
        };

        let refresh = function() {
            window.location.reload();
        };

        let reset_timeout = function() {
            if (timeout) window.clearTimeout(timeout);
            timeout = window.setTimeout(refresh, delay);

            bar.classList.remove('refresh-bar');
            void bar.offsetWidth;
            bar.classList.add('refresh-bar');
            bar.innerText = Math.floor(delay / 1000) + 's';

            if (bar_interval) window.clearInterval(bar_interval);
            bar_interval = window.setInterval(function() { bar.innerText = (parseInt(bar.innerText.replace('/s$/', '')) - 1) + 's'; }, 1000);
        };

        document.addEventListener("mousemove", reset_timeout, false);
        document.addEventListener("mousedown", reset_timeout, false);
        document.addEventListener("keydown", reset_timeout, false);
        document.addEventListener("touchmove", reset_timeout, false);
        document.addEventListener("scroll", reset_timeout, false);

        // // TODO: debounce


        install_bar();
        reset_timeout();

    };

    $('.order-form form').on('submit', function(e) {
        $('.order-form [type=submit]')
            .attr('disabled', 'disabled')
            .val('Please Wait');
    });
})();
