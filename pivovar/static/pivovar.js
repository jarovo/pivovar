const wm_url = `http://${location.hostname}:5001`;

var pivovar_state = {
    wash_machines: {},

    updateWashMachine(wm_id, new_state) {
        Vue.set(this.wash_machines, wm_id, new_state);
    },

    updateWashMachineTempLog(wm_id, new_state) {
        Vue.set(this.wash_machines[wm_id], 'plot_data', new_state);
    }
};

fetch(wm_url + '/wash_machine')
    .then(response => response.json())
    .catch(error => console.error('Error:', error))
    .then(response => {
        pivovar_state.updateWashMachine(response.name, response);
    }
);

function update_data() {
    Object.keys(pivovar_state.wash_machines).forEach(wash_machine_id => {
        $.getJSON(wm_url + '/temp_log', function (temp_log) {
            pivovar_state.updateWashMachineTempLog(wash_machine_id, temp_log);
        }).fail(function() {
            console.error(`Pivovar: Error getting the ${wash_machine_id} temp_log.`);
        });
    });
}

function update_temp_log(wash_machine_id, temp_log) {
    const data = [{
        x: temp_log.datetime,
        y: temp_log.temps,
        mode: 'lines+markers',
        name: '{templota}',
        line: {'shape': 'spline'},
        type: 'scatter'
    }];

    const layout = {
      legend: {
        y: 0.5,
        traceorder: 'reversed',
        font: {size: 16},
        yref: 'paper'
    }};

    Plotly.react(wash_machine_id + "_temp_plot", data, layout);
}

window.setInterval(update_data, 2000);

Vue.component('wash-machine', {
    props: ['wm_name'],
    template: `
    <div class="wash-machine" v-bind:id="wm_name" >
      <h3>{{ $t("Keg Washer", { wm_name }) }}</h3>
      <div class="col-sm-3">
        <h3>{{ $t("Phases") }}</h3>
        <draggable
          id="phases"
          tag="ol"
          class="list-group"
          handle=".handle"
          ghost-class="ghost"
          v-model="phases"
          group="phases"
        >
          <wash-machine-phase v-for="phase_name in phases" :wm_id="wm_name" :phase_name="phase_name"></wash-machine-phase>
        </draggable>
      </div>
      <div class="col-sm-9">
        <h3>{{ $t("water temp in time") }}</h3>
        <div v-bind:id="plot_id" />
      </div>
    </div>`,

    data: function() {
        return {
            phases: pivovar_state.wash_machines[this.wm_name].phases,
        };
    },

    computed: {
        plot_id: function() { return this.wm_name + '_temp_plot'; },
        // plot_data: Object.is(wash_machines[this.wm_name], undefined) ? {} : wash_machines[this.wm_name].plot_data;
        plot_data: function() { return pivovar_state.wash_machines[this.wm_name].plot_data; }
    },

    watch: {
        plot_data: function (val, oldVal) {
            update_temp_log(this.wm_name, val);
        },
    },
});

Vue.component('wash-machine-phase', {
    props: ['wm_id', 'phase_name'],
    template: `
      <li class="list-group-item">
        <i class="handle glyphicon glyphicon-move"></i>{{ phase_name }}
      </li>`,
});

const WashMachines = {
    template: `
        <div>
            <wash-machine v-for="(item, key, index) in wash_machines"
                          :key="item.name"
                          v-bind:wm_name="key"
            ></wash-machine>
        </div>`,
    data: function () {
        return { wash_machines: pivovar_state.wash_machines  };
    }
};

const Fermenters = {
    template: '<div>Spilka</div>'
};

const routes = [
    { path: '/wash_machines', component: WashMachines },
    { path: '/fermenters', component: Fermenters }
];

const router = new VueRouter({
    routes
});

var pivovar = new Vue({
    i18n,
    el: '#pivovar',
    router,
});

