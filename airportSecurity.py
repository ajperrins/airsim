import simpy
import random


# We vary these two parameters to find suitable values to meet our 15 minute max
# passenger wait time goal
NumBoardingPassCheckers = 8
NumSecurityScanners = 4


Lambda1PassengerArrivalsPerMin = 5  # Problem param
MuPassengerArrivalRatePerMin = 1 / Lambda1PassengerArrivalsPerMin
MuBoardingPassServiceTime = 0.75  # Problem param
SimulationRunTimeInMinutes = 100


class AirportSecurity(object):
    def __init__(self, env):
        self.env = env

        # There's a single FIFO queue for the next available boarding pass
        # checker, so this acts as a single SimPy resource with a capacity matching
        # the number of workers
        self.boardingPassCheckers = simpy.Resource(env,
                                                   capacity=NumBoardingPassCheckers)

        # Security scanners are queued separately (the queueing behavior is one
        # whereby the shortest queue is used for the next completed boarding-pass
        # traveler). Since the queues are separate, we set up independent resources
        self.securityScanners = []
        i = 0
        while i < NumSecurityScanners:
            self.securityScanners.append(simpy.Resource(self.env, 1))
            i = i + 1

    def shortest_security_queue(self, person):
        """
        Gets the security queue resource with the shortest queue
        """
        i = 0
        shortest_queue_index = 0
        while i < len(self.securityScanners):
            if i == 0 or len(self.securityScanners[i].queue) < \
                    len(self.securityScanners[shortest_queue_index].queue):
                shortest_queue_index = i
                person.shortest_queue = i
            i = i + 1

        return self.securityScanners[shortest_queue_index]

    def check_passenger(self):
        check_time = random.expovariate(MuBoardingPassServiceTime)
        yield self.env.timeout(check_time)

    def security_scan(self):
        uniform_dist_scan_time = random.uniform(0.5, 1)
        yield self.env.timeout(uniform_dist_scan_time)


class Passenger(object):
    def __init__(self, env, airport, num):
        self.env = env
        self.arrival_time = 0
        self.started_check_time = 0
        self.finished_check_time = 0
        self.started_security_time = 0
        self.shortest_queue = 0
        self.num = num
        self.airport = airport

    def get_waittime(self):
        return (self.started_check_time - self.arrival_time) + \
               (self.started_security_time - self.finished_check_time)

    def go_through_system(self, env):
        global total_passenger_wait_time

        # We track several time-stamps including arrival time to determine
        # duration between events
        self.arrival_time = self.env.now
        with self.airport.boardingPassCheckers.request() as wait_for_checker:
            yield wait_for_checker

            self.started_check_time = env.now

            yield env.process(self.airport.check_passenger())

            self.finished_check_time = env.now

            shortest_queue_resource = self.airport.shortest_security_queue(self)
            with shortest_queue_resource.request() as wait_for_security:
                yield wait_for_security

                # And now that we've been granted the security resource
                # ie. gone through the scanner queue, we run the scan
                # wait simulation which has a uniform distribution wait time
                yield env.process(self.airport.security_scan())

                self.started_security_time = env.now
                total_passenger_wait_time = total_passenger_wait_time + self.get_waittime()

                # We could track other attributes - like security/check time, total time
                # and throughput. The following is commented out to prevent excessive verbosity
                # in the R-markdown output

                #  print("%s wait time %f.... arrived at %f, started check at %f and finished \
                #   processing at %f, started sec at %f. Shortest queue %i" %
                #     (self,
                #      self.get_waittime(),
                #      self.arrival_time,
                #      self.started_check_time,
                #      self.finished_check_time,
                #      self.started_security_time,
                #      self.shortest_queue))

    def __str__(self):
        return "Person_%d" % self.num

def run(env):
    global passenger_count

    airport = AirportSecurity(env)
    # Add passengers into the system on a Poisson distribution with lambda (average interval between
    # arrivals) of `Lambda1PassengerArrivalInterval`
    while True:
        passenger = Passenger(env, airport, passenger_count)
        passenger_count = passenger_count + 1

        # The expovariate function produces numbers fitting an exponential distribution where the numbers
        # are the arrival times between passengers
        yield env.timeout(random.expovariate(1 / MuPassengerArrivalRatePerMin))
        env.process(passenger.go_through_system(env))


total_passenger_wait_time = 0
passenger_count = 0


def run_simulation(sn):
    global total_passenger_wait_time
    global passenger_count

    total_passenger_wait_time = 0
    passenger_count = 0

    simpyenv = simpy.Environment()
    simpyenv.process(run(simpyenv))
    simpyenv.run(until=SimulationRunTimeInMinutes)
    avg_wait_time = total_passenger_wait_time / passenger_count
    print("Sim %d: avg wait time %f minutes" % (sn, avg_wait_time))
    return avg_wait_time


Simulations = 20
total = 0


for x in range(1, Simulations):
    total = total + run_simulation(x)
print("\nAvg simulation wait time %f" % (total / Simulations))

