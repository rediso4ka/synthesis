import stormpy
import stormpy.synthesis

import paynt.quotient.quotient

import collections

import logging
logger = logging.getLogger(__name__)


class MdpFamilyQuotientContainer(paynt.quotient.quotient.QuotientContainer):

    @staticmethod
    def extract_choice_labels(mdp):
        '''
        :param mdp having a canonic choice labeling (exactly 1 label for each choice)
        :return a list of action labels
        :return for each row, its action
        :return for each state, a list of actions associated with the rows of this state
        '''
        assert mdp.has_choice_labeling, "MDP does not have a choice labeling"
        action_labels = list(mdp.choice_labeling.get_labels())
        # sorting because get_labels() is not deterministic
        action_labels = sorted(action_labels)
        label_to_action = {label:index for index,label in enumerate(action_labels)}
        
        choice_to_action = [None] * mdp.nr_choices
        for state in range(mdp.nr_states):
            for choice in mdp.transition_matrix.get_rows_for_group(state):
                label = list(mdp.choice_labeling.get_labels_of_choice(choice))[0]
                action = label_to_action[label]
                choice_to_action[choice] = action

        return action_labels,choice_to_action

    @staticmethod
    def map_state_action_to_choices(mdp, num_actions, choice_to_action):
        state_action_choices = []
        for state in range(mdp.nr_states):
            action_choices = [[] for action in range(num_actions)]
            for choice in mdp.transition_matrix.get_rows_for_group(state):
                action = choice_to_action[choice]
                action_choices[action].append(choice)
            state_action_choices.append(action_choices)
        return state_action_choices

    @staticmethod
    def map_state_to_available_actions(state_action_choices):
        state_to_actions = []
        for state,action_choices in enumerate(state_action_choices):
            available_actions = []
            for action,choices in enumerate(action_choices):
                if choices:
                    available_actions.append(action)
            state_to_actions.append(available_actions)
        return state_to_actions

    
    def __init__(self, quotient_mdp, coloring, specification):
        super().__init__(quotient_mdp = quotient_mdp, coloring = coloring, specification = specification)

        self.design_space = paynt.quotient.holes.DesignSpace(coloring.holes)

        # number of distinct actions in the quotient
        self.num_actions = None
        # a list of action labels
        self.action_labels = None
        # for each choice of the quotient, the executed action
        self.choice_to_action = None
        # for each state of the quotient and for each action, a list of choices that execute this action
        self.state_action_choices = None
        # for each state of the quotient, a list of available actions
        self.state_to_actions = None

        self.action_labels,self.choice_to_action = MdpFamilyQuotientContainer.extract_choice_labels(self.quotient_mdp)
        self.num_actions = len(self.action_labels)
        self.state_action_choices = MdpFamilyQuotientContainer.map_state_action_to_choices(
            self.quotient_mdp, self.num_actions, self.choice_to_action)
        self.state_to_actions = MdpFamilyQuotientContainer.map_state_to_available_actions(self.state_action_choices)

    def empty_policy(self):
        return self.empty_scheduler()

    def scheduler_to_policy(self, scheduler, mdp):            
        state_to_choice = self.scheduler_to_state_to_choice(mdp,scheduler)
        policy = self.empty_policy()
        for state in range(self.quotient_mdp.nr_states):
            choice = state_to_choice[state]
            if choice is not None:
                policy[state] = self.choice_to_action[choice]
        return policy


    def fix_policy_for_family(self, family, policy):
        '''
        Apply policy to the quotient MDP for the given family. If a state is reached for which policy does not define
        an action, pick an arbitrary one.
        :return fixed policy
        :return choice mask from which Q-MDP x policy can be constructed
        '''
        
        choice_mask = stormpy.BitVector(self.quotient_mdp.nr_choices,False)
        policy_fixed = self.empty_policy()

        initial_state = list(self.quotient_mdp.initial_states)[0]
        tm = self.quotient_mdp.transition_matrix
        
        state_visited = stormpy.BitVector(self.quotient_mdp.nr_states,False)
        state_visited.set(initial_state,True)
        state_queue = [initial_state]
        while state_queue:
            state = state_queue.pop()
            action = policy[state]
            if action is None:
                action = self.state_to_actions[state][0]
            policy_fixed[state] = action
            for choice in self.state_action_choices[state][action]:
                if not family.selected_actions_bv[choice]:
                    continue
                choice_mask.set(choice,True)
                for dst in self.choice_destinations[choice]:
                    if not state_visited[dst]:
                        state_visited.set(dst,True)
                        state_queue.append(dst)
        return policy_fixed,choice_mask

    
    def apply_policy_to_family(self, family, policy):
        _,choice_mask = self.fix_policy_for_family(family,policy)
        return self.build_from_choice_mask(choice_mask)


    def assert_mdp_is_deterministic(self, mdp, family):
        if mdp.is_deterministic:
            return
        
        logger.error(f"applied policy to a singleton family {family} and obtained MDP with nondeterminism")
        for state in range(mdp.model.nr_states):

            choices = mdp.model.transition_matrix.get_rows_for_group(state)
            if len(choices)>1:
                quotient_state = mdp.quotient_state_map[state]
                quotient_choices = [mdp.quotient_choice_map[choice] for choice in choices]
                state_str = self.quotient_mdp.state_valuations.get_string(quotient_state)
                state_str = state_str.replace(" ","")
                state_str = state_str.replace("\t","")
                actions_str = [self.action_labels[self.choice_to_action[choice]] for choice in quotient_choices]
                logger.error(f"the following state {state_str} has multiple actions {actions_str}")
        logger.error("aborting...")
        exit(1)
        

    def build_game_abstraction_solver(self, prop):
        target_label = prop.get_target_label()
        precision = paynt.verification.property.Property.model_checking_precision
        solver = stormpy.synthesis.GameAbstractionSolver(
            self.quotient_mdp, len(self.action_labels), self.choice_to_action, target_label, precision
        )
        return solver

    