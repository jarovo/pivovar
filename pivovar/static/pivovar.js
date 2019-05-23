wm_url = "http://localhost:5001"
wash_machines = {}

const messages = {
  en: {
    brewery: "Brewery",
    "water temp in time": 'Water temp in time.',
  },
  cs: {
    brewery: "Pivovar",
    "Phases": "Fáze",
    "Keg Washer": 'Myčka sudů:',
    "water temp in time": 'Teplota vody v čase.',
    "Wash machines": "Myčky",
    "Fermenters": "Spilky",
  }
}

// Create VueI18n instance with options
const i18n = new VueI18n({
  locale: navigator.languages ? navigator.languages[0]
            : (navigator.language || navigator.userLanguage),
  fallbackLocale: 'en',
  messages, // set locale messages
})


fetch(wm_url + '/wash_machine')
    .then(response => response.json())
    .catch(error => console.error('Error:', error))
    .then(response => {
        Vue.set(wash_machines, response.name, response);
        Vue.set(wash_machines[response.name], 'plot_data', {
            datetime: [], temps:[]})
    });

function update_data() {
    Object.keys(wash_machines).forEach(wash_machine_id => {
        const data = { datetime: [ 1, 2, 3], temps: [1, 3, 2] }
        //$.getJSON(wm_url + 'temp_log', function (data) {
        //})

        wash_machines[wash_machine_id].plot_data = data
    })
}

function update_temp_log(wash_machine_id, temp_log) {
    const data = [{
        x: temp_log['datetime'],
        y: temp_log['temps'],
        mode: 'lines+markers',
        name: '{templota}',
        line: {'shape': 'spline'},
        type: 'scatter'
    }]

    const layout = {legend: {
        y: 0.5,
        traceorder: 'reversed',
        font: {size: 16},
        yref: 'paper'
    }};

    Plotly.react(wash_machine_id + "_temp_plot", data, layout);
};

window.setInterval(update_data, 2000)

console.info(wash_machines['wash_machine_1'])
Vue.component('wash-machine', {
    props: ['wm_name'],
    template: `
    <div class="wash-machine" v-bind:id="wm_name" >
      <h3>{{ $t("Keg Washer") }} {{wm_name}}</h3>
      <div class="col-sm-3">
        <h3>{{ $t("Phases") }}</h3>
        <ol id="phases" class="list-group" >
          <wash-machine-phase v-for="phase_name in phases" :wm_id="wm_name" :phase_name="phase_name"></wash-machine-phase>
        </ol>
      </div>
      <div class="col-sm-9">
        <h3>{{ $t("water temp in time") }}</h3>
        <div v-bind:id="plot_id" />
      </div>
    </div>
    `,
    computed: {
        phases: function() { return wash_machines[this.wm_name]['phases'] },
        plot_id: function() { return this.wm_name + '_temp_plot' },
        // plot_data: Object.is(wash_machines[this.wm_name], undefined) ? {} : wash_machines[this.wm_name].plot_data;
        plot_data: function() { return wash_machines[this.wm_name].plot_data }
    },

    watch: {
        plot_data: function (val, oldVal) {
            console.log(val, oldVal)
            update_temp_log(this.wm_name, val)
        },
    },

    mounted () {
        var adjustment;

        $("#phases").sortable({
            handle: 'i.icon-move',
            placeholder: '<li class="placeholder list-group-item"></li>',
            onDrop: function ($item, container, _super) {
                var $clonedItem = $('<li/>').css({height: 0});
                $item.before($clonedItem);
                $clonedItem.animate({'height': $item.height()});

                $item.animate($clonedItem.position(), function  () {
                    $clonedItem.detach();
                    _super($item, container);
                });
            },

            // set $item relative to cursor position
            onDragStart: function ($item, container, _super) {
                var offset = $item.offset(),
                    pointer = container.rootGroup.pointer;

                adjustment = {
                    left: pointer.left - offset.left,
                    top: pointer.top - offset.top
                };

                _super($item, container);
            },

            onDrag: function ($item, position) {
                $item.css({
                    left: position.left - adjustment.left,
                    top: position.top - adjustment.top
                });
            }
        });
    }
});

Vue.component('wash-machine-phase', {
    props: ['wm_id', 'phase_name'],
    template: '<li class="list-group-item"><i class="icon-move glyphicon glyphicon-move"></i>{{ phase_name }}</li>',
});

const WashMachines = {
    template: '<div><wash-machine v-for="(item, key, index) in wash_machines" :key="item.name" v-bind:wm_name="key"></wash-machine></div>',
    data: function () {
        return { wash_machines }
    }
}

const Fermenters = {
    template: '<div>Spilka</div>'
}

const routes = [
    { path: '/wash_machines', component: WashMachines },
    { path: '/fermenters', component: Fermenters }
];

const router = new VueRouter({
    routes
});

var vm = new Vue({
    i18n,
    el: '#pivovar',
    router,
});
