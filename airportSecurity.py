import simpy
import random


Lambda1PassengerArrivalsPerMin = 5  # Problem param
MuPassengerArrivalRatePerMin = 1/Lambda1PassengerArrivalsPerMin  # Implied problem param
MuBoardingPassServiceTime = 0.75  # Problem param

NumBoardingPassCheckers = 5
NumSecurityScanners = 7

SimulationRunTimeInMinutes = 60 * 6

AvgPersonWaitTimePerIteration = []
# AvgPersonBoardingPassCheckTimePerIteration
# AvgPersonScanTimePerIteration
# AvgPersonTimeInSystem


class AirportSecurity(object):
    def __init__(self, env):
        self.env = env

        # There's a single FIFO queue for the next available boarding pass checker, so this
        # acts as a single SimPy resource with a capacity matching the number of workers
        self.boardingPassCheckers = simpy.Resource(env, capacity=NumBoardingPassCheckers)

        # Security scanners are queued separately (the queueing behavior is one whereby the
        # shortest queue is used for the next completed boarding-pass traveler). Since the
        # queues are separate, we set up independent resources
        self.securityScanners = []
        i = 0
        while i < NumSecurityScanners:
            self.securityScanners.append(simpy.Resource(self.env, 1))
            i = i + 1

    def check_passenger(self, passenger):
        check_time = random.expovariate(MuBoardingPassServiceTime)
        yield self.env.timeout(check_time)


class Passenger(object):
    def __init__(self, env, num):
        self.env = env
        self.arrival_time = 0
        self.num = num

    def go_through_system(self, env):
        self.arrival_time = self.env.now
        with airport.boardingPassCheckers.request() as wait_for_checker:
            yield wait_for_checker

            started_check_time = env.now
            yield env.process(airport.check_passenger(self))

            print("%s arrived at %f, started check at %f and finished processing at %f" %
                  (self, self.arrival_time, started_check_time, env.now))
            # duration of service at boarding pass checker
            # yield env.timeout(random.uniform(1, 5))  # todo: rem

    def __str__(self):
        return "Person_%d" % self.num


def run(env):
    # Add passengers into the system on a Poisson distribution with lambda (average interval between
    # arrivals) of `Lambda1PassengerArrivalInterval`
    person_num = 0
    while True:
        passenger = Passenger(env, person_num)
        person_num = person_num + 1

        # The expovariate function produces numbers fitting an exponential distribution where the numbers
        # are the arrival times between passengers
        yield env.timeout(random.expovariate(1 / MuPassengerArrivalRatePerMin))
        env.process(passenger.go_through_system(env))

# def person(env):
#     while True:
#         print("Started parking at %d" % env.now)
#         yield env.timeout(5)
#         print("Started driving at %d" % env.now)


simpyenv = simpy.Environment()
airport = AirportSecurity(simpyenv)
simpyenv.process(run(simpyenv))
simpyenv.run(until=SimulationRunTimeInMinutes)
