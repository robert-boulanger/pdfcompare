import { Menu } from '@tauri-apps/api/menu/menu';
import { Submenu } from '@tauri-apps/api/menu/submenu';
import { MenuItem } from '@tauri-apps/api/menu/menuItem';
import { PredefinedMenuItem } from '@tauri-apps/api/menu/predefinedMenuItem';

export interface MenuActions {
	openLeft: () => void;
	openRight: () => void;
	save: () => void;
	compare: () => void;
	toggleSidebar: () => void;
	toggleSync: () => void;
}

export async function setupAppMenu(actions: MenuActions): Promise<void> {
	const fileMenu = await Submenu.new({
		text: 'File',
		items: [
			await MenuItem.new({ text: 'Open Left PDF', accelerator: 'CmdOrCtrl+O', action: actions.openLeft }),
			await MenuItem.new({ text: 'Open Right PDF', accelerator: 'CmdOrCtrl+Shift+O', action: actions.openRight }),
			await PredefinedMenuItem.new({ item: 'Separator' }),
			await MenuItem.new({ text: 'Save Annotations', accelerator: 'CmdOrCtrl+S', action: actions.save }),
			await PredefinedMenuItem.new({ item: 'Separator' }),
			await PredefinedMenuItem.new({ item: 'Quit' }),
		],
	});

	const viewMenu = await Submenu.new({
		text: 'View',
		items: [
			await MenuItem.new({ text: 'Compare', accelerator: 'CmdOrCtrl+D', action: actions.compare }),
			await PredefinedMenuItem.new({ item: 'Separator' }),
			await MenuItem.new({ text: 'Toggle Sidebar', action: actions.toggleSidebar }),
			await MenuItem.new({ text: 'Toggle Scroll Sync', action: actions.toggleSync }),
			await PredefinedMenuItem.new({ item: 'Separator' }),
			await PredefinedMenuItem.new({ item: 'Fullscreen' }),
		],
	});

	const editMenu = await Submenu.new({
		text: 'Edit',
		items: [
			await PredefinedMenuItem.new({ item: 'Copy' }),
			await PredefinedMenuItem.new({ item: 'SelectAll' }),
		],
	});

	const helpMenu = await Submenu.new({
		text: 'Help',
		items: [
			await MenuItem.new({ text: 'About PDF Compare', enabled: false }),
		],
	});

	const menu = await Menu.new({
		items: [fileMenu, editMenu, viewMenu, helpMenu],
	});

	await menu.setAsAppMenu();
}
