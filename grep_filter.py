# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 by Simmo Saan <simmo.saan@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# History:
#
# 2015-08-25, Simmo Saan <simmo.saan@gmail.com>
#   version 0.6: imitate search settings in filter
# 2015-08-25, Simmo Saan <simmo.saan@gmail.com>
#   version 0.5: option for bar item text
# 2015-08-25, Simmo Saan <simmo.saan@gmail.com>
#   version 0.4: option for default state
# 2015-08-25, Simmo Saan <simmo.saan@gmail.com>
#   version 0.3: allow toggling during search
# 2015-08-25, Simmo Saan <simmo.saan@gmail.com>
#   version 0.2: add bar item for indication
# 2015-08-25, Simmo Saan <simmo.saan@gmail.com>
#   version 0.1: initial script
#

"""
Filter buffers automatically while searching them
"""

from __future__ import print_function

SCRIPT_NAME = "grep_filter"
SCRIPT_AUTHOR = "Simmo Saan <simmo.saan@gmail.com>"
SCRIPT_VERSION = "0.6"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Filter buffers automatically while searching them"

SCRIPT_COMMAND = SCRIPT_NAME
SCRIPT_BAR_ITEM = SCRIPT_NAME
SCRIPT_LOCALVAR = SCRIPT_NAME

IMPORT_OK = True

try:
	import weechat
except ImportError:
	print("This script must be run under WeeChat.")
	print("Get WeeChat now at: http://www.weechat.org/")
	IMPORT_OK = False

SETTINGS = {
	"enable": (
		"off",
		"enable automatically start filtering when searching"),
	"bar_item": (
		"grep",
		"text to show in bar item when filtering")
}

KEYS = {
	"ctrl-G": "/%s toggle" % SCRIPT_COMMAND
}

def get_merged_buffers(ptr):
	hdata = weechat.hdata_get("buffer")
	buffers = weechat.hdata_get_list(hdata, "gui_buffers")
	buffer = weechat.hdata_search(hdata, buffers, "${buffer.number} == %i" % weechat.hdata_integer(hdata, ptr, "number"), 1)
	nbuffer = weechat.hdata_move(hdata, buffer, 1)

	ret = []
	while buffer:
		ret.append(weechat.hdata_string(hdata, buffer, "full_name"))

		if (weechat.hdata_integer(hdata, buffer, "number") == weechat.hdata_integer(hdata, nbuffer, "number")):
			buffer = nbuffer
			nbuffer = weechat.hdata_move(hdata, nbuffer, 1)
		else:
			buffer = None

	return ret

def filter_exists(name):
	hdata = weechat.hdata_get("filter")
	filters = weechat.hdata_get_list(hdata, "gui_filters")
	filter = weechat.hdata_search(hdata, filters, "${filter.name} == %s" % name, 1)

	return bool(filter)

def filter_del(name):
	weechat.command(weechat.buffer_search_main(), "/filter del %s" % name)

def filter_addreplace(name, buffers, tags, regex):
	if filter_exists(name):
		filter_del(name)

	weechat.command(weechat.buffer_search_main(), "/filter add %s %s %s %s" % (name, buffers, tags, regex))

def buffer_searching(buffer):
	hdata = weechat.hdata_get("buffer")

	return bool(weechat.hdata_integer(hdata, buffer, "text_search"))

def buffer_filtering(buffer):
	local = weechat.buffer_get_string(buffer, "localvar_%s" % SCRIPT_LOCALVAR)
	return {"": None, "0": False, "1": True}[local]

def buffer_build_regex(buffer):
	hdata = weechat.hdata_get("buffer")
	input = weechat.hdata_string(hdata, buffer, "input_buffer")
	exact = weechat.hdata_integer(hdata, buffer, "text_search_exact")
	where = weechat.hdata_integer(hdata, buffer, "text_search_where")

	if exact:
		input = "(?-i)%s" % input

	regex = None
	if where == 1: # message
		regex = input
	elif where == 2: # prefix
		regex = "%s\\t" % input
	else: # prefix | message
		regex = input # TODO: impossible with current filter regex

	return "!%s" % regex

def buffer_update(buffer):
	hdata = weechat.hdata_get("buffer")

	buffers = ",".join(get_merged_buffers(buffer))
	name = "%s_%s" % (SCRIPT_NAME, buffers)

	if buffer_searching(buffer):
		if buffer_filtering(buffer) and not filter_exists(name):
			filter_addreplace(name, buffers, "*", buffer_build_regex(buffer))
		elif not buffer_filtering(buffer) and filter_exists(name):
			filter_del(name)
	elif filter_exists(name):
		filter_del(name)

	where = weechat.hdata_integer(hdata, buffer, "text_search_where")
	weechat.buffer_set(buffer, "localvar_set_%s_warn" % SCRIPT_LOCALVAR, "1" if where == 3 else "0") # warn about incorrect filter

	weechat.bar_item_update(SCRIPT_BAR_ITEM)

def input_search_cb(data, signal, buffer):
	if buffer_searching(buffer) and buffer_filtering(buffer) is None:
		enable = weechat.config_string_to_boolean(weechat.config_get_plugin("enable"))
		weechat.buffer_set(buffer, "localvar_set_%s" % SCRIPT_LOCALVAR, "1" if enable else "0")
		weechat.buffer_set(buffer, "localvar_set_%s_warn" % SCRIPT_LOCALVAR, "0")
	elif not buffer_searching(buffer):
		weechat.buffer_set(buffer, "localvar_del_%s" % SCRIPT_LOCALVAR, "")
		weechat.buffer_set(buffer, "localvar_del_%s_warn" % SCRIPT_LOCALVAR, "")

	buffer_update(buffer)

	return weechat.WEECHAT_RC_OK

def input_text_changed_cb(data, signal, buffer):
	if buffer_searching(buffer) and buffer_filtering(buffer):
		buffers = ",".join(get_merged_buffers(buffer))
		name = "%s_%s" % (SCRIPT_NAME, buffers)

		filter_addreplace(name, buffers, "*", buffer_build_regex(buffer))

	return weechat.WEECHAT_RC_OK

def command_cb(data, buffer, args):
	if args == "enable":
		weechat.buffer_set(buffer, "localvar_set_%s" % SCRIPT_LOCALVAR, "1")
	elif args == "disable":
		weechat.buffer_set(buffer, "localvar_set_%s" % SCRIPT_LOCALVAR, "0")
	elif args == "toggle":
		weechat.buffer_set(buffer, "localvar_set_%s" % SCRIPT_LOCALVAR, "0" if buffer_filtering(buffer) else "1")
	else:
		pass

	buffer_update(buffer)

	return weechat.WEECHAT_RC_OK

def bar_item_cb(data, item, window, buffer, extra_info):
	buffers = ",".join(get_merged_buffers(buffer))
	name = "%s_%s" % (SCRIPT_NAME, buffers)

	if filter_exists(name):
		warn = int(weechat.buffer_get_string(buffer, "localvar_%s_warn" % SCRIPT_LOCALVAR))

		return "%s%s%s" % (
			weechat.color("input_text_not_found" if warn else "bar_fg"),
			weechat.config_get_plugin("bar_item"),
			weechat.color("reset"))
	else:
		return ""

if __name__ == "__main__" and IMPORT_OK:
	if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
		weechat.hook_signal("input_search", "input_search_cb", "")
		weechat.hook_signal("input_text_changed", "input_text_changed_cb", "")

		weechat.hook_command(SCRIPT_COMMAND, SCRIPT_DESC,
"""enable
 || disable
 || toggle""",
""" enable: enable grep_filter in current buffer
disable: disabe grep_filter in current buffer
 toggle: toggle grep_filter in current buffer""",
"""enable
 || disable
 || toggle""",
		"command_cb", "")

		weechat.bar_item_new("(extra)%s" % SCRIPT_BAR_ITEM, "bar_item_cb", "")

		for option, value in SETTINGS.items():
			if not weechat.config_is_set_plugin(option):
				weechat.config_set_plugin(option, value[0])

			weechat.config_set_desc_plugin(option, "%s (default: \"%s\")" % (value[1], value[0]))

		weechat.key_bind("search", KEYS)
