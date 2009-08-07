#  Copyright 2009, Patrick C. McGinty

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
   A multi-threaded work pool interface.
"""

import threading
import Queue

__author__ = 'Patrick C. McGinty'
__email__ = 'flacsync@tuxcoder.com'


class WorkerQueue( Queue.Queue ):
   """Extended Queue class w/ additional 'apply' method."""
   def apply( self, fn, *args, **kwargs ):
      self.put( (fn, args, kwargs) )


class Worker( threading.Thread ):
   """Genearlized worker thread. Each queue item is a callable "work unit" to
   be completed by the thread."""

   POLL_INTERVAL = 0.2

   dismiss  = threading.Event()  # thread exit event
   queue    = WorkerQueue()      # shared work queue

   def run( self ):
      is_keyint_exc = False   # set after KeyboardInterrupt exception
      while not self.dismiss.is_set():
         try:
            func,args,kwargs = self.queue.get(timeout=self.POLL_INTERVAL)
            try:
               if not is_keyint_exc:
                  func( *args, **kwargs )
            except KeyboardInterrupt:
               # disable work and clear out remaining queue items
               is_keyint_exc = True
            finally:
               self.queue.task_done()
         except Queue.Empty:
            pass


def pool( size ):
   """Create a pool of worker threads. Returns a shared queue watched by all
   workers."""
   for i in xrange(size):
      Worker().start()
   return Worker.queue

def pool_stop():
   Worker.dismiss.set()

