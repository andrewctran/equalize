import random
import matplotlib.pyplot as plt
import itertools
import graph
import equalize as eq_new
import equalized_flow as eq_old

exp = ['1221', '1239', '1755', '3257', '3967', '6461']
num_rep_server = 5
num_rep_client = 64
MAX_DELAY = 20 # how do i set this?
MAX_DIFFERENCE = 2
num_trials = 5

DD_tolerance = 0.05
L_overhead = 1

def Experiment(g):
    random.seed()

    eq_old_diff = {}
    eq_new_diff = {}
    eq_old_delay = {}
    eq_new_delay = {}
    ospf_diff = {}
    ospf_delay = {}
    
    nodes = set(g.getNodes())
    possible_servers = [s for s in nodes if len(g.getNeighbors(s)) > 1]
    print possible_servers

    for s in possible_servers:
        possible_clients = list(nodes)
        possible_clients.remove(s)
        max_shortest_path = max([g.getDistance(c,s) for c in possible_clients])

        #print max_shortest_path

        eq_old_diff[s] = {}
        eq_new_diff[s] = {}
        eq_old_delay[s] = {}
        eq_new_delay[s] = {}
        ospf_diff[s] = {}
        ospf_delay[s] = {}

        print 'server ', s

        for num_clients in range(2, 5):
            eq_old_diff[s][num_clients] = {}
            eq_new_diff[s][num_clients] = {}
            eq_old_delay[s][num_clients] = {}
            eq_new_delay[s][num_clients] = {} 
            ospf_diff[s][num_clients] = {}
            ospf_delay[s][num_clients] = {}

            eqo_list = []
            eqn_list = []
            ospf_list = []

            for i in range(num_trials):
                print '\ttrial ', i
                clients = random.sample(possible_clients, num_clients)

                ospf_all_delays = [g.getDistance(c,s) for c in clients]
                ospf_list.append(ospf_all_delays)
                print '\t\tospf ', ospf_all_delays
                #print ospf_all_delays


                print '\t\teqo'
                eqo = eq_old.EqualizedFlow(g)
                eqo.registerService(s, 0, DD_tolerance, L_overhead)
                #c = clients[-1]
                #eqo.addClients(s, 0, (c,))
                eqo.addClients(s, 0, clients)
                eqo_paths = eqo.getPaths(s, 0)
                eqo_all_delays = sorted([eqo.pathLength(s,0,c) for c in clients])
                eqo_list.append(eqo_all_delays)
                print '\t\t\t', eqo_all_delays
                #print eqo_all_delays

                print '\t\teqn'
                eqn = eq_new.EqualizedFlow(g)
                eqn.registerService({s}, 0, max(ospf_all_delays), 0)
                eqn.addClients(0, clients)
                removed_clients = eqn.removedClients(0)
                current_clients = eqn.registeredClients(0)
                eqn_paths = {c:eqn.getPaths(0,c) for c in current_clients}
                eqn_all_delays = sorted([eqn.getPathLength(0,c) for c in current_clients])
                eqn_list.append(eqn_all_delays)
                print '\t\t\t', eqn_all_delays
                #print eqn_all_delays

                '''if eqo_all_delays != eqn_all_delays:
                    print eqo_all_delays
                    print eqn_all_delays'''
            eqo_avg, eqo_max = computeDelay(eqo_list)
            eq_old_delay[s][num_clients]['avg'] = eqo_avg
            eq_old_delay[s][num_clients]['max'] = eqo_max
            eqo_avg, eqo_max = computeData(eqo_list, num_clients)
            eq_old_diff[s][num_clients]['avg'] = eqo_avg
            eq_old_diff[s][num_clients]['max'] = eqo_max

            eqn_avg, eqn_max = computeDelay(eqn_list)
            eq_new_delay[s][num_clients]['avg'] = eqn_avg
            eq_new_delay[s][num_clients]['max'] = eqn_max
            eqn_avg, eqn_max = computeData(eqn_list, num_clients)
            eq_new_diff[s][num_clients]['avg'] = eqn_avg
            eq_new_diff[s][num_clients]['max'] = eqn_max

            ospf_avg, ospf_max = computeDelay(ospf_list)
            ospf_delay[s][num_clients]['avg'] = ospf_avg
            ospf_delay[s][num_clients]['max'] = ospf_max
            ospf_avg, ospf_max = computeData(ospf_list, num_clients)
            ospf_diff[s][num_clients]['avg'] = ospf_avg
            ospf_diff[s][num_clients]['max'] = ospf_max
    return [(ospf_delay, ospf_diff), (eq_old_delay, eq_old_diff), (eq_new_delay, eq_new_diff)]

def computeDelay(data):
    l = [getAverage(vl) for vl in data]
    avg = getAverage(l)
    m = [max(vl) for vl in data]
    mx = max(m)
    return avg, mx

def getAverage(l):
    return float(sum(l)) / len(l)

def computeData(data, n):
    l = [getPariwiseDelay(d, n) for d in data]
    avg = sum([v[0] for v in l]) / float(n)
    mx = max([v[1] for v in l])
    return (avg, mx)

def getPariwiseDelay(l, n):
    l = [abs(c1-c2) for c1, c2 in itertools.combinations(l,2)]
    num = n * (n-1) / 2.0
    return (sum(l)/num, max(l))
        

def averageOverServers(l):
    toReturn = {}
    for n_clients in l[0].keys():
        toReturn[n_clients] = {}
        allavg = [l[s][n_clients]['avg'] for s in l.keys()]
        allmax = [l[s][n_clients]['max'] for s in l.keys()]

        toReturn[n_clients]['avg'] = getAverage(allavg)
        toReturn[n_clients]['max'] = max(allmax)
    return toReturn

def separateKeyAndVal(d):
    keys = d.keys()
    vals = [d[k] for k in keys]

    return keys,vals


if __name__ == '__main__':
    #g = graph.createRocketFuelGraph('../rocketfuel/3967/latencies.intra')
    g = graph.createAbileneGraph()
    ans = Experiment(g)

    ret = [(averageOverServers(a[0]), averageOverServers(a[1])) for a in ans]

    ospf_delay_max = {c: ret[0][0][c]['max'] for c in ret[0][0]}
    o_x, o_y = separateKeyAndVal(ospf_delay_max)
    leq_o_delay_max = {c: ret[1][0][c]['max'] for c in ret[1][0]}
    lo_x, lo_y = separateKeyAndVal(leq_o_delay_max)
    leq_n_delay_max = {c: ret[2][0][c]['max'] for c in ret[2][0]}
    ln_x, ln_y = separateKeyAndVal(leq_n_delay_max)

    fig1 = plt.figure()
    ax = fig1.add_subplot(111)
    ax.spines['left'].set_position('zero')
    ax.spines['right'].set_color('none')
    ax.spines['bottom'].set_position('zero')
    ax.spines['top'].set_color('none')
    ax.spines['left'].set_smart_bounds(True)
    ax.spines['bottom'].set_smart_bounds(True)
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')
    ax.axhline(linewidth=2, color='blue')
    ax.axvline(linewidth=2, color='blue')
    ax.plot(o_x,o_y,'r--',lo_x,lo_y,'bs:',ln_x,ln_y,'g^-.')
    plt.show()

    ospf_diff_max = {c: ret[0][1][c]['max'] for c in ret[0][1]}
    o_x, o_y = separateKeyAndVal(ospf_diff_max)
    leq_o_diff_max = {c: ret[1][1][c]['max'] for c in ret[1][1]}
    lo_x, lo_y = separateKeyAndVal(leq_o_diff_max)
    leq_n_diff_max = {c: ret[2][1][c]['max'] for c in ret[2][1]}
    ln_x, ln_y = separateKeyAndVal(leq_n_diff_max)

    plt.plot(o_x,o_y,'r--',lo_x,lo_y,'bs:',ln_x,ln_y,'g^-.')
    plt.show()

    ospf_delay_avg = {c: ret[0][0][c]['avg'] for c in ret[0][0]}
    o_x, o_y = separateKeyAndVal(ospf_delay_avg)
    leq_o_delay_avg = {c: ret[1][0][c]['avg'] for c in ret[1][0]}
    lo_x, lo_y = separateKeyAndVal(leq_o_delay_avg)
    leq_n_delay_avg = {c: ret[2][0][c]['avg'] for c in ret[2][0]}
    ln_x, ln_y = separateKeyAndVal(leq_n_delay_avg)

    plt.plot(o_x,o_y,'r--',lo_x,lo_y,'bs:',ln_x,ln_y,'g^-.')
    plt.show()

    ospf_diff_avg = {c: ret[0][1][c]['avg'] for c in ret[0][1]}
    o_x, o_y = separateKeyAndVal(ospf_diff_avg)
    leq_o_diff_avg = {c: ret[1][1][c]['avg'] for c in ret[1][1]}    
    lo_x, lo_y = separateKeyAndVal(leq_o_diff_avg)
    leq_n_diff_avg = {c: ret[2][1][c]['avg'] for c in ret[2][1]}
    ln_x, ln_y = separateKeyAndVal(leq_n_diff_avg)

    plt.plot(o_x,o_y,'r--',lo_x,lo_y,'bs:',ln_x,ln_y,'g^-.')
    plt.show()


    '''for r in ret:
        print 'delay ', r[0]
        for r2 in r[0]:
            print 'clients: ', r2
            print 'average: ', r[0][r2]['avg']
            print 'max: ', r[0][r2]['max'], '\n'
        print 'diff ', r[1]
        for r2 in r[1]:
            print 'clients: ', r2
            print 'average: ', r[1][r2]['avg']
            print 'max: ', r[1][r2]['max'], '\n'
            '''