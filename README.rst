Decoupled Neural Interfaces Using Synthetic Gradients
=====================================================

|Build Status| |PyPI version|

.. raw:: html

   <!-- START doctoc generated TOC please keep comment here to allow auto update -->

.. raw:: html

   <!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

-  `Install <#install>`__

   -  `From source <#from-source>`__

-  `Architecure <#architecure>`__
-  `Usage <#usage>`__
-  `Tasks <#tasks>`__

.. raw:: html

   <!-- END doctoc generated TOC please keep comment here to allow auto update -->

This is an implementation of `Decoupled Neural Interfaces using
Synthetic Gradients, Jaderberg et
al. <https://arxiv.org/abs/1608.05343>`__.

Install
-------

.. code:: bash

    pip install pytorch-dni

From source
~~~~~~~~~~~

::

    git clone https://github.com/ixaxaar/pytorch-dni
    cd pytorch-dni
    pip install -r ./requirements.txt
    pip install -e .

Architecure
-----------

Usage
-----

.. code:: python

    from dni import DNI

    # Custom network, can be anything extending nn.Module
    net = WhateverNetwork(**kwargs)
    opt = optim.Adam(net.parameters(), lr=0.001)

    # use DNI to optimize this network
    net = DNI(net, optim=opt)

    # after that we go about our business as usual
    for e in range(epoch):
      opt.zero_grad()
      output = net(input, *args)
      loss = criterion(output, target_output)
      loss.backward()

      # Optional: do this to __also__ update net's weight using backprop
      # opt.step()
    ...

DNI Networks
------------

This package ships with 3 types of DNI networks:

-  RNN_DNI: stacked ``LSTM``\ s, ``GRU``\ s or ``RNN``\ s
-  Linear_DNI: 2-layer ``Linear`` modules
-  Linear_Sigmoid_DNI: 2-layer ``Linear`` followed by ``Sigmoid``

Custom DNI Networks
-------------------

Custom DNI nets can be created using the ``DNI_Network`` interface:

.. code:: python

    class MyDNI(DNI_Network):
      def __init__(self, input_size, hidden_size, output_size, **kwargs):
        super(MyDNI, self).__init__(input_size, hidden_size, output_size)

        self.net = { ... your custom net }
        ...

      def forward(self, input, hidden):
        return self.net(input), None # return (output, hidden), hidden can be None

Tasks
-----

The tasks included in this project are the same as those in
`pytorch-dnc <https://github.com/ixaxaar/pytorch-dnc#tasks>`__, except
that they’re trained here using DNI.

Notable stuff
-------------

-  Using a linear SG module makes the implicit assumption that loss is a
   quadratic function of the activations
-  For best performance one should adapt the SG module architecture to
   the loss function used. For MSE linear SG is a reasonable choice,
   however for log loss one should use architectures including a sigmoid
   applied pointwise to a linear SG
-  Learning rates of the order of ``1e-5`` with momentum of ``0.9``
   works well for rmsprop

.. |Build Status| image:: https://travis-ci.org/ixaxaar/pytorch-dni.svg?branch=master
   :target: https://travis-ci.org/ixaxaar/pytorch-dni
.. |PyPI version| image:: https://badge.fury.io/py/dni.svg
   :target: https://badge.fury.io/py/pytorch-dni
