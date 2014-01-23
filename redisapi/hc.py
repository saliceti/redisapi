# Copyright 2014 redis-api authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.


class FakeHealthCheck(object):
    added = False

    def add(self, host, port):
        self.added = True