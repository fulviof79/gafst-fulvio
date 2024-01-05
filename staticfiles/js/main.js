// htmx configuration for modal dialogs and toast messages
;(function () {
    const modal = new bootstrap.Modal(document.getElementById("modal"))

    htmx.on("htmx:afterSwap", (e) => {
        e.stopPropagation()
        // Response targeting #dialog => show the modal
        if (e.detail.target.id == "dialog") {
            modal.show()
        }
    })

    htmx.on("htmx:beforeSwap", (e) => {
        e.stopPropagation()
        // Empty response targeting #dialog => hide the modal
        if (e.detail.target.id == "dialog" && !e.detail.xhr.response) {
            modal.hide()
            e.detail.shouldSwap = false
        }
    })


    // Remove dialog content after hiding
    htmx.on("hidden.bs.modal", (e) => {
        e.stopPropagation()
        document.getElementById("dialog").innerHTML = ""
    })
})()

// ----- show toast on showMessage event ------------------------------
;(function () {
    const toastElement = document.getElementById("toast")
    const toastBody = document.getElementById("toast-body")
    const toast = new bootstrap.Toast(toastElement, { delay: 2000 })

    htmx.on("showMessage", (e) => {
        toastBody.innerText = e.detail.value
        toast.show()
    })
})()

// ----- show a warning message if minimum members number in team hasn't reached -----
function setWarning() {
    const warning = document.getElementById('warning-message');

    if(!warning) return;

    const minMemberNum = document.querySelector('input[id="team_min_members_number"]')?.value;
    const selectedMembers = document.querySelectorAll('input[name="members"]:checked').length;

    if (selectedMembers >= parseInt(minMemberNum || 0))
        warning.style.display = 'none';
    else
        warning.style.display = 'block';

}

function isACompetitionRegistrationForm() {
    const currentURL = window.location.href;

    // Verifica se siamo in un dialogo di registrazione alla competizione in creazione o modifica
    return !!(currentURL.includes("competition-registration/create/") || currentURL.match(/competition-registration\/\d+\/edit/));

}

// ----- Competition registration confirm dialog --------------
// document.getElementById('modal-save-button').addEventListener('click', function(event) {
//         if (!isACompetitionRegistrationForm) return;
//
//         event.preventDefault(); // Evita l'invio del form
//
//         $.get('{% url "competition_registration_confirm_template" %}', function(data) {
//             if (data.message === 'CONFIRM_REQUIRED') {
//                 $('body').append(data);
//             } else {
//                 document.getElementById('create-form').submit();
//             }
//         });
//
//     });

// ----- DataTables ------------------------------
document.body.addEventListener('htmx:load', function(evt) {
    const newElementTag = evt.detail.elt.localName;
    const id = evt.detail.elt.id;

    const table_id = `#${id}`;
    const container_id = `#${id}_wrapper`;
    const buttons_col_id = `#${id}_buttons_col`;
    const filters_col_id = `#${id}_filters_col`;
    const search_input_id = `#${id}_filter`;
    const add_button_id = `#${id}_add_button`;

    if (newElementTag === 'table' && !$.fn.DataTable.isDataTable(table_id)) {
        let table = $(table_id).DataTable({
            dom:
            //<"` + container_id + `.dataTables_wrapper dt-bootstrap5 no-footer">
                  `<"row"
                    <"${buttons_col_id}.col-sm-12 col-md-6" B>
                    <"${filters_col_id}.col-sm-12 col-md-6" f>
                  >
                  <"row dt-row"
                    <"col-sm-12" tr>
                  >
                  <"row"
                    <"col-sm-12.col-md-5" i>
                    <"col-sm-12.col-md-7" p>
                  >`
            //>
            ,

            language: {
                "decimal":        gettext("."),
                "emptyTable":     gettext("No data available in table"),
                "info":           gettext("Showing _START_ to _END_ of _TOTAL_ entries"),
                "infoEmpty":      gettext("Showing 0 to 0 of 0 entries"),
                "infoFiltered":   gettext("(filtered from _MAX_ total entries)"),
                "infoPostFix":    gettext(""),
                "thousands":      gettext(","),
                "lengthMenu":     gettext("Show _MENU_ entries"),
                "loadingRecords": gettext("Loading..."),
                "processing":     gettext(""),
                "search":         gettext("Search:"),
                "zeroRecords":    gettext("No matching records found"),
                "paginate": {
                    "first":      gettext("First"),
                    "last":       gettext("Last"),
                    "next":       gettext("Next"),
                    "previous":   gettext("Previous")
                },
                "aria": {
                    "sortAscending":  gettext(": activate to sort column ascending"),
                    "sortDescending": gettext(": activate to sort column descending")
                }
            },

            responsive: {
                details: {
                    type: 'column',
                    target: 0,
                    renderer: (api, rowIdx, columns) => {
                        let data = columns.map((col, i) => col.hidden
                            ? `<tr data-dt-row="${col.rowIndex}" data-dt-column="${col.columnIndex}">
                                 <td class="pe-3 fw-semibold">${col.title}:</td>
                                 <td>${col.data}</td>
                               </tr>`
                            : ''
                        ).join('');

                        let table = document.createElement('table');
                        table.innerHTML = data;

                        return data ? table : false;
                    }
                }
            },

            columnDefs: [

                {
                    className: 'dtr-control',
                    orderable: false,
                    targets: 0
                },
                {
                    orderable: false,
                    targets: 1
                },
                { "width": "fit-content", "targets": 1},
            ],
            order: [2, 'asc'],

            lengthChange: false,

            scrollY: "300px",

            paging: true,

            fixedColumns: true,

            buttons: {
                dom: {
                    button: {
                        className: 'btn btn-primary btn-sm'
                    }
                },
                buttons: [
                    {
                        extend: 'collection',
                        text: gettext('Export'),
                        buttons: ['pdf', 'excel', 'csv'],
                        id: 'export',
                        className: 'btn btn-primary btn-sm',
                    },
                ],

            }
        });

        table.buttons().container()
            .appendTo( buttons_col_id );

        $(buttons_col_id).append($(add_button_id))

        // change search bar style
        $(search_input_id).addClass('mt-2 mt-md-0 float-md-end float-start');

        // change export button style
        const export_button = `${container_id} .dt-buttons`;
        $(export_button).addClass('m-0');
        $(export_button).css('width', 'auto');
    }

    setWarning();

    document
        .getElementById('team_min_members_number')
        ?.addEventListener('input', setWarning);

    document
        .querySelectorAll('input[name="members"]')
        ?.forEach(element => element.addEventListener('input', setWarning));

    const disciplineSelect = document.querySelector('select[name="discipline"]');
    if(disciplineSelect)
        disciplineSelect.classList.add('form-select');

    const divisionSelect = document.querySelector('select[name="division"]');
    if(divisionSelect)
        divisionSelect.classList.add('form-select');

    const disciplineContainer = document.getElementById('discipline_container');

    if(!disciplineContainer) return;

    disciplineContainer.addEventListener('change', function(event) {
        const lastDiv = disciplineContainer.lastElementChild;
        let selectedValue = null;

        if (lastDiv.tagName.toLowerCase() === 'div') {
            const selectElement = lastDiv.querySelector('select');

            if (selectElement) {
                if (selectElement.selectedIndex !== -1) {
                    const selectedOption = selectElement.options[selectElement.selectedIndex];
                    selectedValue = selectedOption.value;
                }
            }
        }

        fetch(`/competition-registration/load_divisions?discipline=${selectedValue}`, {
            method: 'GET',
        })
        .then(function(response) {
            return response.text();
        })
        .then(function(data) {
            const divisionContainer = document.getElementById('division_container');
            if(!divisionContainer) return;
            divisionContainer.innerHTML = data;
        })
        .catch(function(error) {
            console.error("Errore:", error);
        });
    });

    const team = document.querySelector('select[name="team"]');

    if(!team) return;

    team.addEventListener('change', function(event) {
        const discipline = document.querySelector('select[name="discipline"]')?.value;
        const division = document.querySelector('select[name="division"]')?.value;

        if(!discipline || !division || !team.value) return;

        fetch(`/check_rules?discipline=${discipline || ""}&division=${division || ""}&team=${team?.value || ""}`, {
            method: 'GET',
        })
        .then(function(response) {
            return response.text();
        })
        .then(function(data) {
            const warningBoxContainer = document.getElementById('registration-warning-container');
            if(!warningBoxContainer) return;
            warningBoxContainer.innerHTML = data;
        })
        .catch(function(error) {
            console.error("Errore:", error);
        });
    });

    const discipline = document.querySelector('select[name="discipline"]')?.value;
    if(!discipline) return;

    const division = document.querySelector('select[name="division"]')?.value;
    if(!division) return;

    const _team = document.querySelector('select[name="team"]')?.value;
    if(!_team) return;

    fetch(`/check_rules?discipline=${discipline || ""}&division=${division || ""}&team=${team?.value || ""}`, {
        method: 'GET',
    })
    .then(function(response) {
        return response.text();
    })
    .then(function(data) {
        const warningBoxContainer = document.getElementById('registration-warning-container');
        if(!warningBoxContainer) return;
        warningBoxContainer.innerHTML = data;
    })
    .catch(function(error) {
        console.error("Errore:", error);
    });
});

// ----- Sidebar toggle ------------------------------

// on click of .toggle-sidebar-btn, toggle the class 'toggle-sidebar' on the body element
$('.toggle-sidebar-btn').on('click', function() {
    $('body').toggleClass('toggle-sidebar');
});

// ---- Boostrap 5 Multiple Select -----------------------
$(document).ready(function() {
    $('.multiple-select').on('change', function(event) {
        if($(this).val().length === 0) {
            $(this).val($(this).data('selected'));
        } else {
            $(this).data('selected', $(this).val());
        }
    });
});

// ---- Language selector -----------------------
function changeLanguage(selectElement) {
    const selectedLanguage = selectElement.value;
    const currentURL = window.location.href;
    const baseURL = currentURL.split('?')[0];  // Remove query parameters if any
    const newURL = baseURL.replace(/\/\w{2}\//, `/${selectedLanguage}/`);
    window.location.href = newURL;
}
