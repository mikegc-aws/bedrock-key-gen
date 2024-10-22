import curses
from collections import defaultdict

class TreeMenu:
    def __init__(self, items, include_all=True, title=None, question=None, single_select=False):
        self.providers = defaultdict(list)
        self.use_groups = False
        self.include_all = include_all
        self.title = title
        self.question = question
        self.single_select = single_select
        self.items = items
        for item in items:
            if 'groupName' in item:
                self.use_groups = True
                self.providers[item['groupName']].append(item)
            else:
                self.providers[''].append(item)
        self.menu_items = list(self.providers.keys()) if self.use_groups else self.providers['']
        self.expanded = set()
        self.current_selection = 0
        self.top_line = 0
        self.selected_items = set()
        self.selected_groups = set()

    def get_flat_menu(self):
        flat_menu = []
        if self.include_all:
            flat_menu.append(('all', {'label': 'All', 'value': '*'}))
        if self.use_groups:
            for provider in self.menu_items:
                flat_menu.append(('provider', provider))
                if provider in self.expanded:
                    for model in self.providers[provider]:
                        flat_menu.append(('model', model))
        else:
            for item in self.menu_items:
                flat_menu.append(('model', item))
        return flat_menu

    def display(self, stdscr):
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        y = 0
        if self.title:
            stdscr.addstr(y, 0, self.title[:width-1])
            y += 1
        if self.question:
            stdscr.addstr(y, 0, self.question[:width-1])
            y += 1
        
        flat_menu = self.get_flat_menu()
        max_display = height - y - 1
        
        for i in range(max_display):
            item_index = self.top_line + i
            if item_index >= len(flat_menu):
                break
            
            item_type, item = flat_menu[item_index]
            y_pos = y + i
            x = 2
            
            if item_type == 'provider':
                prefix = '▼ ' if item in self.expanded else '▶ '
                selection_indicator = '*' if item in self.selected_groups else ' '
                label = f"{selection_indicator}{prefix}{item}"[:width-4]
            else:
                label = item['label'][:width-8]
                if self.single_select:
                    selection_indicator = '*' if item['value'] == self.selected_items else ' '
                else:
                    selection_indicator = '*' if item['value'] in self.selected_items else ' '
                label = f"{selection_indicator} {label}"
                if self.use_groups and item_type != 'all':
                    label = f"    {label}"
            
            if item_index == self.current_selection:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y_pos, x, label)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addstr(y_pos, x, label)
        
        if self.single_select:
            stdscr.addstr(height-1, 0, "↑↓: Move, Enter: Select")
        else:
            stdscr.addstr(height-1, 0, "↑↓: Move, →←: Expand/Collapse, Space: Select, Enter: Confirm")
        stdscr.refresh()

    def _run_menu(self, stdscr):
        curses.curs_set(0)  # Hide the cursor
        self.display(stdscr)

        while True:
            key = stdscr.getch()
            flat_menu = self.get_flat_menu()
            
            if key == curses.KEY_UP and self.current_selection > 0:
                self.current_selection -= 1
                if self.current_selection < self.top_line:
                    self.top_line = self.current_selection
            elif key == curses.KEY_DOWN and self.current_selection < len(flat_menu) - 1:
                self.current_selection += 1
                if self.current_selection >= self.top_line + curses.LINES - 3:
                    self.top_line = self.current_selection - curses.LINES + 4
            elif key == curses.KEY_RIGHT and not self.single_select:
                if flat_menu[self.current_selection][0] == 'provider':
                    self.expanded.add(flat_menu[self.current_selection][1])
            elif key == curses.KEY_LEFT and not self.single_select:
                if flat_menu[self.current_selection][0] == 'provider':
                    self.expanded.discard(flat_menu[self.current_selection][1])
            elif key == ord(' ') and not self.single_select:
                item_type, item = flat_menu[self.current_selection]
                if item_type == 'model':
                    if item['value'] in self.selected_items:
                        self.selected_items.remove(item['value'])
                    else:
                        self.selected_items.add(item['value'])
                elif item_type == 'provider':
                    if item in self.selected_groups:
                        self.selected_groups.remove(item)
                        for model in self.providers[item]:
                            self.selected_items.discard(model['value'])
                    else:
                        self.selected_groups.add(item)
                        for model in self.providers[item]:
                            self.selected_items.add(model['value'])
                elif item_type == 'all':
                    if len(self.selected_items) == len(self.items):
                        self.selected_items.clear()
                        self.selected_groups.clear()
                    else:
                        self.selected_items = set(item['value'] for item in self.items)
                        self.selected_groups = set(self.providers.keys())
            elif key == ord('\n'):  # Enter key
                if self.single_select:
                    item_type, item = flat_menu[self.current_selection]
                    if item_type == 'model':
                        return [item['value']]
                elif self.selected_items:
                    return list(self.selected_items)
            
            self.display(stdscr)

    def run(self):
        return curses.wrapper(self._run_menu)
