#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import torch as T
from torch.autograd import Variable as var
import torch.nn.functional as F
import torch.optim as optim
import torch.nn as nn

from .rnn_dni import RNN_DNI
from .output_format import *

class DNI(nn.Module):

  def __init__(self, network, dni_network=None, optim=None, grad_optim='adam', grad_lr=0.001, hidden_size=None):
    super(DNI, self).__init__()

    # the DNI network generator
    self.dni_network = RNN_DNI if dni_network is None else dni_network

    # the network and optimizer for the entire network
    self.network = network
    self.network_optimizer = \
      optim if optim is not None else self.get_optim(self.network.parameters(), grad_optim, grad_lr)

    # optim params for the DNI networks' optimizers
    self.grad_optim = grad_optim
    self.lr = grad_lr
    # optim params for the network's per-layer optimizers
    self.optim = str(self.network_optimizer.__class__.__name__).lower()

    # DNI synthetic gradient networks (for each module in network)
    self.dni_networks = {}
    self.dni_networks_data = {}

    self.forward_hooks = []
    self.backward_hooks = []
    # lock that prevents the backward and forward hooks to act respectively
    self.backward_lock = False
    self.forward_lock = False

    # hidden size of the DNI network
    self.hidden_size = 57 if hidden_size is None else hidden_size

    # register forward and backward hooks to all leaf modules in the network
    self.register_forward(self.network, self._forward_update_hook)
    self.register_backward(self.network, self._backward_update_hook)

  def register_forward(self, network, hook):
    for module in network.modules():
      # register hooks only to leaf nodes in the graph with at least 1 learnable Parameter
      l = 0
      for x in module.children(): l += 1
      p = sum([ 1 for x in module.parameters() ])

      if l == 0 and p > 0:
        # register forward hooks
        h = hook()
        print('Registering forward hooks for ' + str(module))
        module.register_forward_hook(h)
        self.forward_hooks += [{ "name": str(module), "id": id(module), "hook": h }]

  def register_backward(self, network, hook):
    for module in network.modules():
      # register hooks only to leaf nodes in the graph with at least 1 learnable Parameter
      l = 0
      for x in module.children(): l += 1
      p = sum([ 1 for x in module.parameters() ])

      if l == 0 and p > 0:
        # register backward hooks
        h = hook()
        print('Registering backward hooks for ' + str(module))
        module.register_backward_hook(h)
        self.backward_hooks += [{ "name": str(module), "id": id(module), "hook": h }]

  def _forward_update_hook(self):
    def hook(module, input, output):
      if self.forward_lock:
        return

      print('Forward hook called for ' + str(module))
      output = format(output, module)

      # create DNI networks and optimizers if they dont exist (for this module)
      if id(module) not in list(self.dni_networks.keys()):
        self.dni_networks[id(module)] = self.dni_network(
          input_size=output.size(-1),
          hidden_size=self.hidden_size,
          output_size=output.size(-1)
        )
        self.dni_networks_data[id(module)] = {}
        # the gradient module's (DNI network) optimizer
        self.dni_networks_data[id(module)]['grad_optim'] = \
          self.get_optim(self.dni_networks[id(module)].parameters(), otype=self.grad_optim)
        # the network module's optimizer
        self.dni_networks_data[id(module)]['optim'] = \
          self.get_optim(module.parameters(), otype=self.optim)

      self.dni_networks_data[id(module)]['optim'].zero_grad()

      # get the DNI network's hidden state
      hx = self.dni_networks_data[id(module)]['hidden'] if 'hidden' in self.dni_networks_data[id(module)] else None

      # pass through the DNI network, get updated gradients for the host network
      grad, hx = self.dni_networks[id(module)](output, None)
      # backprop with generated gradients
      self.backward_lock = True
      output.backward(grad.detach())
      self.backward_lock = False
      # parameter = parameter - grad - try subtractive directly on param weights!
      # can inhibitory neurons be gradient estimators? :O
      self.dni_networks_data[id(module)]['optim'].step()

      # store the hidden state and gradient
      self.dni_networks_data[id(module)]['hidden'] = hx
      self.dni_networks_data[id(module)]['grad'] = grad
    return hook

  def _backward_update_hook(self):
    def hook(module, grad_input, grad_output):
      if self.backward_lock:
        return

      print('Backward hook called for ' + str(module))
    return hook

  def forward(self, *kwargs):
    ret = self.network(*kwargs)

    # since the DNI net gets created after the frist forward pass, create its sequential and optimizer here
    if not self.dni_network:
      self.dni_network = nn.Sequential(*list(self.dni_networks.values()))
      self.dni_optimizer = self.get_optim(self.dni_network.parameters(), otype=self.optim, lr=self.lr)
    return ret

  def backward(self, loss):
    return self.network.backward(loss)

  def get_optim(self, parameters, otype="adam", lr=0.001):
    if type(otype) is str:
      if otype == 'adam':
        optimizer = optim.Adam(parameters, lr=lr, eps=1e-9, betas=[0.9, 0.98]) # 0.0001
      elif otype == 'adamax':
        optimizer = optim.Adamax(selfparameters, lr=lr, eps=1e-9, betas=[0.9, 0.98]) # 0.0001
      elif otype == 'rmsprop':
        optimizer = optim.RMSprop(parameters, lr=lr, momentum=0.9, eps=1e-10) # 0.0001
      elif otype == 'sgd':
        optimizer = optim.SGD(parameters, lr=lr) # 0.01
      elif otype == 'adagrad':
        optimizer = optim.Adagrad(parameters, lr=lr)
      elif otype == 'adadelta':
        optimizer = optim.Adadelta(parameters, lr=lr)

    return optimizer


