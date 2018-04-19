# Pivovar.

[![Build Status](https://travis-ci.org/jaryn/pivovar.svg?branch=master)](https://travis-ci.org/jaryn/pivovar)

## Algorithm.

### Phases.

1. Heating
The water in the storage tank is being heated to temperature defined in the
configuration. Algorithm waits for the water to get the defined temperature.
2. Prewash. LED 1.1 glows.
3. Draining. LED 1.2 glows.
4. Washing with lye. LED 1.3 glows.
5. Rinsing with cold water. LED 1.4 glows.
6. Washing with hot water. LED X2 glows.
7. Drying. LED X3 glows.
8. Filing with CO2. LED X4 glows.

## Sources.
[https://dspace.cvut.cz/handle/10467/63696]
