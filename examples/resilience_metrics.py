from __future__ import print_function
import wntr
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

def topographic_metrics(wn):
    # Get a copy of the graph
    G = wn.get_graph()

    # Print general topographic information
    print(nx.info(G))

    # Plot node and edge attributes.
    junction_attr = wn.query_node_attribute('elevation',
                                          node_type=wntr.network.Junction)
    pipe_attr = wn.query_link_attribute('length', link_type=wntr.network.Pipe)
    wntr.graphics.plot_network(wn, node_attribute=junction_attr,
                               link_attribute=pipe_attr,
                               title='Node elevation and pipe length',
                               node_size=40, link_width=2)

    # Compute link density
    print("Link density: " + str(nx.density(G)))

    # Compute node degree
    node_degree = dict(G.degree())
    wntr.graphics.plot_network(wn, node_attribute=node_degree,
                          title='Node Degree', node_size=40, node_range=[1,5])

    # Compute number of terminal nodes
    terminal_nodes = G.terminal_nodes()
    wntr.graphics.plot_network(wn, node_attribute=terminal_nodes,
                          title='Terminal nodes', node_size=40, node_range=[0,1])
    print("Number of terminal nodes: " + str(len(terminal_nodes)))
    print("   " + str(terminal_nodes))

    # Compute pipes with diameter > threshold
    diameter = 0.508 # m (20 inches)
    pipes = wn.query_link_attribute('diameter', np.greater, diameter)
    wntr.graphics.plot_network(wn, link_attribute=list(pipes.keys()),
                          title='Pipes > 20 inches', link_width=2,
                          link_range=[0,1])
    print("Number of pipes > 20 inches: " + str(len(pipes)))
    print("   " + str(pipes))

    # Compute nodes with elevation <= treshold
    elevation = 1.524 # m (5 feet)
    nodes = wn.query_node_attribute('elevation', np.less_equal, elevation)
    wntr.graphics.plot_network(wn, node_attribute=list(nodes.keys()),
                          title='Nodes <= 5 ft elevation', node_size=40,
                          node_range=[0,1])
    print("Number of nodes <= 5 ft elevation: " + str(len(nodes)))
    print("   " + str(nodes))

    # Compute eccentricity, diameter, and average shortest path length
    # These all use an undirected graph
    uG = G.to_undirected() # undirected graph
    if nx.is_connected(uG):
        ecc = nx.eccentricity(uG)
        wntr.graphics.plot_network(wn, node_attribute=ecc, title='Eccentricity',
                              node_size=40, node_range=[15, 30])

        print("Diameter: " + str(nx.diameter(uG)))

        ASPL = nx.average_shortest_path_length(uG)
        print("Average shortest path length: " + str(ASPL))

    # Compute cluster coefficient
    clust_coefficients = nx.clustering(nx.Graph(G))
    wntr.graphics.plot_network(wn, node_attribute=clust_coefficients,
                          title='Clustering Coefficient', node_size=40)

    # Compute betweenness centrality
    bet_cen = nx.betweenness_centrality(G)
    wntr.graphics.plot_network(wn, node_attribute=bet_cen,
                          title='Betweenness Centrality', node_size=40,
                          node_range=[0, 0.4])
    central_pt_dom = G.central_point_dominance()
    print("Central point dominance: " + str(central_pt_dom))

    # Compute articulation points
    Nap = list(nx.articulation_points(uG))
    Nap = list(set(Nap)) # get the unique nodes in Nap
    Nap_density = float(len(Nap))/uG.number_of_nodes()
    print("Density of articulation points: " + str(Nap_density))
    wntr.graphics.plot_network(wn, node_attribute=Nap, title='Articulation Point',
                          node_size=40, node_range=[0,1])

    # Compute bridges
    bridges = G.bridges()
    wntr.graphics.plot_network(wn, link_attribute=bridges, title='Bridges',
                          link_width=2, link_range=[0,1])
    Nbr_density = float(len(bridges))/G.number_of_edges()
    print("Density of bridges: " + str(Nbr_density))

    # Compute spectal gap
    spectral_gap = G.spectral_gap()
    print("Spectal gap: " + str(spectral_gap))

    # Compute algebraic connectivity
    alg_con = G.algebraic_connectivity()
    print("Algebraic connectivity: " + str(alg_con))

    # Critical ratio of defragmentation
    fc = G.critical_ratio_defrag()
    print("Critical ratio of defragmentation: " + str(fc))

    # Compute closeness centrality
    clo_cen = nx.closeness_centrality(G)
    wntr.graphics.plot_network(wn, node_attribute=clo_cen,
                          title='Closeness Centrality', node_size=40)

def hydraulic_metrics(wn):
    # Set nominal pressure
    for name, node in wn.junctions():
        node.nominal_pressure = 15

    # Simulate hydraulics
    sim = wntr.sim.WNTRSimulator(wn, mode='PDD')
    results = sim.run_sim()

    # Create list of node names
    junctions = [name for name, node in wn.junctions()]

    # Define pressure lower bound
    P_lower = 21.09 # m (30 psi)

    # Query pressure
    pressure = results.node['pressure'].loc[:,junctions]
    mask = wntr.metrics.query(pressure, np.greater, P_lower)
    pressure_regulation = mask.all(axis=0).sum() # True over all time
    print("Fraction of nodes > 30 psi: " + str(pressure_regulation))
    print("Average node pressure: " +str(pressure.mean().mean()) + " m")
    wntr.graphics.plot_network(wn, node_attribute=pressure.min(axis=0), node_size=40,
                          title= 'Min pressure')

    # Compute todini index
    head = results.node['head']
    pressure = results.node['pressure']
    demand = results.node['demand']
    flowrate = results.link['flowrate']
    todini = wntr.metrics.todini_index(head, pressure, demand, flowrate, wn, P_lower)
    plt.figure()
    plt.plot(todini)
    plt.ylabel('Todini Index')
    plt.xlabel('Time, hr')
    print("Todini Index")
    print("  Mean: " + str(np.mean(todini)))
    print("  Max: " + str(np.max(todini)))
    print("  Min: " + str(np.min(todini)))

    # Create a weighted graph for flowrate at time 36 hours
    t = 36*3600
    attr = results.link['flowrate'].loc[t,:]
    G_flowrate_36hrs = wn.get_graph()
    G_flowrate_36hrs.weight_graph(link_attribute=attr)

    # Compute betweenness-centrality at time 36 hours
    bet_cen = nx.betweenness_centrality(G_flowrate_36hrs)
    wntr.graphics.plot_network(wn, node_attribute=bet_cen,
                          title='Betweenness Centrality', node_size=40)
    central_pt_dom = G_flowrate_36hrs.central_point_dominance()
    print("Central point dominance: " + str(central_pt_dom))

    # Compute entropy at time 36, for node 185
    [S, Shat] = wntr.metrics.entropy(G_flowrate_36hrs, sources=None, sinks=['185'])

    # Plot all simple paths between the Lake/River and node 185
    link_count = G_flowrate_36hrs.links_in_simple_paths(sources=['Lake', 'River'], sinks=['185'])
    wntr.graphics.plot_network(wn, link_attribute=link_count, link_width=1,
                            node_attribute = {'River': 1, 'Lake': 1, '185': 1},
                            node_size=30, title='Link count in paths')

    # Calculate entropy for 1 day, all nodes
    shat = []
    G_flowrate_t = wn.get_graph()
    for t in np.arange(0, 24*3600+1,3600):
        attr = results.link['flowrate'].loc[t,:]
        G_flowrate_t.weight_graph(link_attribute=attr)
        entropy = wntr.metrics.entropy(G_flowrate_t)
        shat.append(entropy[1])
    plt.figure()
    plt.plot(shat)
    plt.ylabel('System Entropy')
    plt.xlabel('Time, hr')
    print("Entropy")
    print("  Mean: " + str(np.mean(shat)))
    print("  Max: " + str(np.nanmax(shat)))
    print("  Min: " + str(np.nanmin(shat)))

    # Compute water service availability, for each junction
    expected_demand = wntr.metrics.expected_demand(wn)
    demand = results.node['demand'].loc[:,wn.junction_name_list]
    wsa = wntr.metrics.water_service_availability(expected_demand.sum(axis=0), 
                                                  demand.sum(axis=0))
    wntr.graphics.plot_network(wn, node_attribute=wsa, node_size=40, node_range=[0,1], 
                               title='Water service availability, averaged over times')

def water_quality_metrics(wn):
    # Simulate hydraulics and water quality
    sim = wntr.sim.EpanetSimulator(wn)
    wn.options.quality.mode = 'CHEMICAL'
    source_pattern = wntr.network.elements.Pattern.binary_pattern('SourcePattern', 
            start_time=2*3600, end_time=15*3600, duration=wn.options.time.duration, 
            step_size=wn.options.time.pattern_timestep)
    wn.add_pattern('SourcePattern', source_pattern)
    wn.add_source('Source1', '121', 'SETPOINT', 1000, 'SourcePattern')
    wn.add_source('Source2', '123', 'SETPOINT', 1000, 'SourcePattern')
    results_CHEM = sim.run_sim()
    
    wn.options.quality.mode = 'AGE'
    results_AGE = sim.run_sim()
    
    wn.options.quality.mode = 'TRACE'
    wn.options.quality.trace_node = '111'
    results_TRACE = sim.run_sim()

    # plot chem scenario
    CHEM_at_5hr = results_CHEM.node['quality'].loc[ 5*3600, :]
    wntr.graphics.plot_network(wn, node_attribute=CHEM_at_5hr, node_size=20,
                          title='Chemical concentration, time = 5 hours')
    CHEM_at_node = results_CHEM.node['quality'].loc[ :, '208']
    plt.figure()
    CHEM_at_node.plot(title='Chemical concentration, node 208')

    # Plot age scenario (convert to hours)
    AGE_at_5hr = results_AGE.node['quality'].loc[ 5*3600, :]/3600.0
    wntr.graphics.plot_network(wn, node_attribute=AGE_at_5hr, node_size=20,
                          title='Water age (hrs), time = 5 hours')
    AGE_at_node = results_AGE.node['quality'].loc[ :, '208']/3600.0
    plt.figure()
    AGE_at_node.plot(title='Water age, node 208')

    # Plot trace scenario
    TRACE_at_5hr = results_TRACE.node['quality'].loc[ 5*3600, :]
    wntr.graphics.plot_network(wn, node_attribute=TRACE_at_5hr, node_size=20,
                          title='Trace percent, time = 5 hours')
    TRACE_at_node = results_TRACE.node['quality'].loc[ :, '208']
    plt.figure()
    TRACE_at_node.plot(title='Trace percent, node 208')

    # Calculate average water age (last 48 hours)
    age = results_AGE.node['quality']
    age_last_48h = age.loc[age.index[-1]-48*3600:age.index[-1]]/3600
    age_last_48h.index = age_last_48h.index/3600
    age_last_48h.plot(legend=False)
    plt.ylabel('Water age (h)')
    plt.xlabel('Time (h)')
    wntr.graphics.plot_network(wn, node_attribute=age_last_48h.mean(),
                          title='Average water age (last 48 hours)', node_size=40)
    print("Average water age (last 48 hours): " +str(age_last_48h.mean().mean()) + " hr")

    # Query concentration
    chem_upper_bound = 750
    chem = results_CHEM.node['quality']
    mask = wntr.metrics.query(chem, np.greater, chem_upper_bound)
    chem_regulation = mask.any(axis=0) # True for any time
    wntr.graphics.plot_network(wn, node_attribute=chem_regulation, node_size=40,
                          title= 'Nodes with conc > upper bound')
    wntr.graphics.plot_network(wn, node_attribute=chem.max(axis=0), node_size=40,
                          title= 'Max concentration')
    print("Fraction of nodes > chem upper bound: " + str(chem_regulation.sum()))
    print("Average node concentration: " +str(chem.mean().mean()))

def water_security_metrics(wn):
    # Define WQ scenario
    wn.options.quality.mode = 'CHEMICAL'
    # Source pattern already exists
    # source_pattern = wntr.network.elements.Pattern.binary_pattern('SourcePattern', step_size=wn.options.time.pattern_timestep, start_time=2*3600, end_time=15*3600, duration=wn.options.time.duration)
    # wn.add_pattern('SourcePattern', source_pattern)
    wn.add_source('Source1', '121', 'SETPOINT', 1000, 'SourcePattern')

    # Simulate hydraulics and water quality for each scenario
    sim = wntr.sim.EpanetSimulator(wn)
    results_CHEM = sim.run_sim()

    demand = results_CHEM.node['demand'].loc[:,wn.junction_name_list]
    quality = results_CHEM.node['quality'].loc[:,wn.junction_name_list]
    flowrate = results_CHEM.link['flowrate'].loc[:,wn.pipe_name_list] 
    
    MC = wntr.metrics.mass_contaminant_consumed(demand, quality)
    VC = wntr.metrics.volume_contaminant_consumed(demand, quality, 0.001)
    EC = wntr.metrics.extent_contaminant(quality, flowrate, wn, 0.001)

    wntr.graphics.plot_network(wn, node_attribute=MC.sum(axis=0), node_range = [0,400], node_size=40,
                          title='Total mass consumed')

    plt.figure()
    EC.plot(title='Extent of contamination')


def population_impacted_metrics(wn):
    # Compute population per node
    pop = wntr.metrics.population(wn)
    total_population = pop.sum()
    print("Total population: " + str(total_population))
    wntr.graphics.plot_network(wn, node_attribute=pop, node_range = [0,400], node_size=40,
                          title='Population, Total = ' + str(total_population))

    # Find population and nodes impacted by pressure less than 40 m
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()
    pressure = results.node['pressure'].loc[:,wn.junction_name_list]
    pop_impacted = wntr.metrics.population_impacted(pop, pressure, np.less, 40)
    plt.figure()
    pop_impacted.sum(axis=1).plot(title='Total population with pressure < 40 m')
    nodes_impacted = wntr.metrics.query(pressure, np.less, 40)
    wntr.graphics.plot_network(wn, node_attribute=nodes_impacted.any(axis=0), node_size=40,
                          title='Nodes impacted')

def cost_ghg_metrics(wn):
    # Copute network cost
    network_cost = wntr.metrics.annual_network_cost(wn)
    print("Network cost: $" + str(round(network_cost,2)))

    # COmpute green house gas emissions
    network_ghg = wntr.metrics.annual_ghg_emissions(wn)
    print("Network GHG emissions: " + str(round(network_ghg,2)))


if __name__ == '__main__':
    # Create a water network model
    inp_file = 'networks/Net3.inp'
    wn = wntr.network.WaterNetworkModel(inp_file)

    # Compute resilience metrics
    topographic_metrics(wn)
    hydraulic_metrics(wn)
    water_quality_metrics(wn)
    water_security_metrics(wn)
    population_impacted_metrics(wn)
    cost_ghg_metrics(wn)
