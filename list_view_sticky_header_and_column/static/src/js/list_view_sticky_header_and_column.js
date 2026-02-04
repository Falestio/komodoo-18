/** @odoo-module **/
/** This file will used to stick the selected header and column in  the list view **/
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
    },
    _getStickyContainer() {
        return this.el || this.__owl__.bdom.parentEl.querySelector('.o_list_renderer') || this.__owl__.bdom.parentEl;
    },
    /**
     * function defining the button having t-on-click _onClick
     */
    _onClickIcon(ev, column) {
    ev.preventDefault();
        ev.stopPropagation();
        const clickedHeader = ev.currentTarget.closest('th');
        const columnIndex = Array.from(clickedHeader.parentNode.children).indexOf(clickedHeader);
        const container = this._getStickyContainer();
        if (!container) {
            return;
        }
        // Remove 'sticky-column' and 'clicked-header' classes from relevant elements
        const stickyColumns = container.querySelectorAll('.sticky-column');
        stickyColumns.forEach(el => el.classList.remove('sticky-column'));
        const clickedHeaders = container.querySelectorAll('.clicked-header');
        clickedHeaders.forEach(el => el.classList.remove('clicked-header'));

        // Add 'clicked-header' class to the clicked header
        clickedHeader.classList.add('clicked-header');

        // Select table headers, rows, and footer
        const listTable = container.querySelector('.o_list_table');
        if (!listTable) {
            return;
        }
        const tableHeaders = listTable.querySelectorAll('th');
        const tableRows = listTable.querySelectorAll('tr');
        const tfootRowCells = listTable.querySelector('tfoot tr')?.children || [];

        // Select footer cells up to columnIndex (inclusive)
        const selectedFooterCells = Array.from(tfootRowCells).slice(0, columnIndex + 1);
        selectedFooterCells.forEach(cell => cell.classList.add('sticky-column'));

        // Select data row cells and header cells up to columnIndex (inclusive)
        const selectedColumns = listTable.querySelectorAll(
            `.o_data_row td:nth-child(-n+${columnIndex + 1})`
        );
        const selectedHeaderCells = Array.from(tableHeaders).slice(0, columnIndex + 1);

        // Remove 'sticky-column' class and 'left' style from all headers and data cells
        tableHeaders.forEach(header => {
            header.classList.remove('sticky-column');
            header.style.left = '';
        });
        listTable.querySelectorAll('.o_data_row td').forEach(cell => {
            cell.classList.remove('sticky-column');
            cell.style.left = '';
        });

        // Add 'sticky-column' class to selected columns and headers
        selectedColumns.forEach(cell => cell.classList.add('sticky-column'));
        selectedHeaderCells.forEach(header => header.classList.add('sticky-column'));

        listTable.querySelectorAll('.sticky-column').forEach(el => {
            if (el.tagName === 'TH') {
                el.style.top = '0';
            }
        });

        // Calculate left position for the target column
        const targetColumn = Array.from(selectedColumns).find(
            (el, idx) => idx % (columnIndex + 1) === columnIndex
        );
        const tableRect = listTable.getBoundingClientRect();

        // Adjust left position for sticky columns in headers and rows
        const columnsToAdjust = columnIndex + 1;
        tableRows.forEach(row => {
            const headerCells = row.querySelectorAll('th');
            const rowCells = row.querySelectorAll('td');
            for (let i = 0; i < columnsToAdjust; i++) {
                if (headerCells[i]) {
                    const leftPos = headerCells[i].getBoundingClientRect().left - tableRect.left;
                    headerCells[i].style.left = `${leftPos}px`;
                }
                if (rowCells[i]) {
                    const leftPos = rowCells[i].getBoundingClientRect().left - tableRect.left;
                    rowCells[i].style.left = `${leftPos}px`;
                }
            }
        });
    },
    /**
     * super onClickSortColumn function and remove the icon and element having the class sticky-column
     */
    onClickSortColumn(column) {
        super.onClickSortColumn(...arguments);
        const container = this._getStickyContainer();
        if (!container) {
            return;
        }
        const stickyColumns = container.querySelectorAll('.sticky-column');
        stickyColumns.forEach(el => el.classList.remove('sticky-column'));
        const clickedHeaders = container.querySelectorAll('.clicked-header');
        clickedHeaders.forEach(el => el.classList.remove('clicked-header'));
        const tableHeaders = container.querySelectorAll('.o_list_table th');
        tableHeaders.forEach(header => {
            header.classList.remove('sticky-column');
            header.style.left = '';
        });
    },
});
