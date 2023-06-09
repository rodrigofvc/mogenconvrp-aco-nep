import numpy as np
import math

class Ant:
    def __init__(self, nest, n, min_pheromone):
        self.nest = nest
        self.arcs_visited = np.zeros((n,n))
        self.min_pheromone = min_pheromone

    def get_remaining_costumers(self, costumers_dh, costumers_attended):
        remaining = []
        remaining = [c for c in costumers_dh if not c in costumers_attended]
        return remaining

    def get_psi_ij(self, costumer_i, costumer_j, day):
        estimated_ij = costumer_i.arrival_times[day] + costumer_i.service_times[day] + costumer_i.distance_to(costumer_j)
        diffs = [(abs(a-estimated_ij)) for a in costumer_j.arrival_times if a > 0] + [0]
        wait_ij = max(diffs)
        psi_ij = 1 / max(1, wait_ij)
        return psi_ij

    def get_phi_j(self, costumer_j, current_vehicle, vehicles):
        different_vehicles = 0
        if current_vehicle.id in costumer_j.vehicles_visit:
            return 1
        different_vehicles = costumer_j.get_max_vehicle_difference()
        phi_j = 1 / max(1, different_vehicles)
        return phi_j

    def get_eta_ij(self, costumer_i, costumer_j):
        eta_ij = 1 / costumer_i.distance_to(costumer_j)
        return eta_ij

    def get_probabilities_from_costumer(self, current_costumer, remaining_costumers, pheromone_matrix, day, timetable, alpha, beta, gamma, delta, Q, current_vehicle, vehicles, explotation):
        probabilities = []
        pheromone_matrix_day_h = pheromone_matrix[timetable][day]
        for remaining_costumer in remaining_costumers:
            i = current_costumer.id
            j = remaining_costumer.id
            if i == j:
                raise()
            pheromone_dh_ij = pheromone_matrix_day_h[i][j]
            eta_ij = self.get_eta_ij(current_costumer, remaining_costumer)
            psi_ij = self.get_psi_ij(current_costumer, remaining_costumer, day)
            phi_j = self.get_phi_j(remaining_costumer, current_vehicle, vehicles)
            prob_ij = max(math.pow(pheromone_dh_ij, alpha), self.min_pheromone) * math.pow(eta_ij, beta) * math.pow(psi_ij,gamma) * math.pow(phi_j, delta)
            probabilities.append(prob_ij)
        if explotation:
            argmax = np.argmax(probabilities)
            probabilities = [0] * len(probabilities)
            probabilities[argmax] = 1
            return probabilities
        total = sum(probabilities)
        probabilities = [p/total for p in probabilities]
        return probabilities


    def get_next_costumer(self, remaining_costumers, current_costumer, alpha, beta, gamma, delta, Q, current_vehicle, pheromone_matrix, day, timetable, vehicles, q0, current_time):
        # check if current_vehicle its on time to arrive at each costumer (including to return depot)
        remaining_costumers = [c for c in remaining_costumers if current_time + current_costumer.distance_to(c) + c.service_times[day] + c.distance_to(self.nest) <= current_vehicle.limit_time]
        if len(remaining_costumers) == 0:
            return None
        if len(remaining_costumers) == 1:
            return remaining_costumers[0]
        q = np.random.rand()
        explotation = False
        if q <= q0:
            explotation = True
        probabilities = self.get_probabilities_from_costumer(current_costumer, remaining_costumers, pheromone_matrix, day, timetable, alpha, beta, gamma, delta, Q, current_vehicle, vehicles, explotation)
        next_costumer = np.random.choice(remaining_costumers, 1, p=probabilities)[0]
        return next_costumer

    def get_costumers_day(self, costumers_dh, day):
        costumers = []
        costumers = [c for c in costumers_dh if c.demands[day] > 0 and c.id != 0]
        return costumers

    def update_delta_matrix(self, delta_ant_matrix, current_vehicle, day, timetable, Q):
        time_tour = current_vehicle.times_tour[day]
        dif_ve = [max(1, c.get_max_vehicle_difference()) for c in current_vehicle.tour[day] if c.id != 0 and not current_vehicle.id in c.vehicles_visit] + [1]
        sat = [max(1, c.get_max_arrival_diference()) for c in current_vehicle.tour[day] if c.id != 0 and day in c.get_worts_days()] + [1]
        dif_ve = max(dif_ve)
        sat = max(sat)
        pheromone = Q / (sat * time_tour * dif_ve)
        self.arcs_visited *= pheromone
        delta_ant_matrix[timetable][day] += self.arcs_visited
        self.arcs_visited = np.zeros(self.arcs_visited.shape)

    # Create a solution for a planning in a specific day, timetable
    def build_solution(self, delta_ant_matrix, pheromone_matrix, day, timetable, alpha, beta, gamma, delta, Q, costumers_dh, vehicles, q0):
        tour = [self.nest]
        current_costumer = tour[0]
        i = 0
        current_vehicle = vehicles[i]
        current_vehicle.set_tour_day(day, tour)
        costumers_attended = []
        costumers_day = self.get_costumers_day(costumers_dh, day)
        current_time = 0
        while len(costumers_attended) != len(costumers_day):
            remaining_costumers = self.get_remaining_costumers(costumers_day, costumers_attended)
            next_costumer = self.get_next_costumer(remaining_costumers, current_costumer, alpha, beta, gamma, delta, Q, current_vehicle, pheromone_matrix, day, timetable, vehicles, q0, current_time)
            # current_vehicle must return to depot (limit time reached)
            if next_costumer == None:
                current_time = 0
                current_vehicle.return_depot(day)
                self.arcs_visited[current_costumer.id][0] = 1
                self.arcs_visited[0][current_costumer.id] = 1
                tour = [self.nest]
                current_costumer = tour[0]
                i += 1
                current_vehicle = vehicles[i]
                current_vehicle.set_tour_day(day, tour)
                next_costumer = self.get_next_costumer(remaining_costumers, current_costumer, alpha, beta, gamma, delta, Q, current_vehicle, pheromone_matrix, day, timetable, vehicles, q0, current_time)

            if current_vehicle.loads[day] + next_costumer.demands[day] <= current_vehicle.capacity:
                current_time = current_vehicle.add_costumer_tour_day(day, next_costumer)
                costumers_attended.append(next_costumer)
                if current_costumer == next_costumer:
                    raise()
                self.arcs_visited[current_costumer.id][next_costumer.id] = 1
                self.arcs_visited[next_costumer.id][current_costumer.id] = 1
                current_costumer = next_costumer
            else:
                current_vehicle.return_depot(day)
                self.arcs_visited[next_costumer.id][0] = 1
                self.arcs_visited[0][next_costumer.id] = 1
                self.update_delta_matrix(delta_ant_matrix, current_vehicle, day, timetable, Q)
                tour = [self.nest]
                current_costumer = tour[0]
                i += 1
                current_vehicle = vehicles[i]
                current_vehicle.set_tour_day(day, tour)
            # No remaining costumers, return to depot
            if len(costumers_attended) == len(costumers_day):
                current_vehicle.return_depot(day)
                self.arcs_visited[next_costumer.id][0] = 1
                self.arcs_visited[0][next_costumer.id] = 1
                self.update_delta_matrix(delta_ant_matrix, current_vehicle, day, timetable, Q)
            #print (f'{len(costumers_attended)} / {len(costumers_dh)}')
