let repository, archive1, archive2, api_url, app_config, template_method, get_path, get_data, sort_function, report_type,
    sorting_reversed = false

const init_core = function (object) {
    repository = object.repository;
    archive1 = object.archive1;
    archive2 = object.archive2;
    template_method = object.template_method;
    get_path = object.get_path;
    get_data = object.get_data;
    report_type = object.report_type;
    api_url = `/api/${object.api_url}`;
}

const init_dom_informations = function () {
    document.getElementById('repository_title').innerHTML = `${query_repo} - ${metadata.short_id} (${get_linux_date_format(metadata.summary.backup_end)})`;
    document.getElementById('snapshot_details').innerHTML =
        `Files changed : ${metadata.summary.files_changed + metadata.summary.files_new}, ` +
        `Data added : ${file_size(metadata.summary.data_added)}, ` +
        `Total size : ${file_size(metadata.summary.total_bytes_processed)} (${metadata.summary.total_files_processed} files)`;

    document.getElementById('command_line_input').value = `${app_config.app.restic_executable_path} --repo "${app_config.repo[query_repo].url}" --password-file ".secrets/${query_repo}" ls "${metadata.short_id}"`;

    document.title = `${query_repo} - ${metadata.short_id}`
}

const remove_all_children = function (dom_object) {
    while (dom_object.firstChild) {
        dom_object.firstChild.remove();
    }
}

const alphabetical_sort = function (a, b) {
    return sorting_reversed ? ('' + b[0]).localeCompare(a[0]) : ('' + a[0]).localeCompare(b[0]);
}

const added_size_sort = function (a, b) {
    let sorting_result = -1;

    if (report_type === "diff") {
        if (a[0] !== '/info' && b[0] !== '/info') {
            const a_added = get_size_delta(a[1]['/info']['changes'][0], "added");
            const b_added = get_size_delta(b[1]['/info']['changes'][0], "added");

            sorting_result = b_added - a_added;
        }
    } else {
        if (a[0] !== '/info' && b[0] !== '/info') {
            const a_added = a[1]['/info']['size']
            const b_added = b[1]['/info']['size']
            sorting_result = b_added - a_added;
        }
    }

    return sorting_reversed ? -sorting_result : sorting_result;
}

const removed_size_sort = function (a, b) {
    let sorting_result = -1;

    if (report_type === "diff") {
        if (a[0] !== '/info' && b[0] !== '/info') {
            const a_removed = get_size_delta(a[1]['/info']['changes'][0], "removed");
            const b_removed = get_size_delta(b[1]['/info']['changes'][0], "removed");

            sorting_result = b_removed - a_removed;
        }
    }

    return sorting_reversed ? -sorting_result : sorting_result;
}

const diff_size_sort = function (a, b) {
    let sorting_result = -1;

    if (report_type === "diff") {
        if (a[0] !== '/info' && b[0] !== '/info') {
            const a_added = get_size_delta(a[1]['/info']['changes'][0], "added");
            const a_removed = get_size_delta(a[1]['/info']['changes'][0], "removed");
            const b_added = get_size_delta(b[1]['/info']['changes'][0], "added");
            const b_removed = get_size_delta(b[1]['/info']['changes'][0], "removed");

            sorting_result = (b_added - b_removed) - (a_added - a_removed);
        }
    }

    return sorting_reversed ? -sorting_result : sorting_result;
}

const build_nested_levels = function (level, nested_level_dom, target) {
    const placeholder_dom = document.createElement('div')
    placeholder_dom.classList.add('placeholder')
    placeholder_dom.innerHTML = "<span class='vr_before'></span><span class='vr' ></span>"

    const nested_header = document.createElement('div')
    nested_header.classList.add('header_content')

    for (let [index, entry] of Object.entries(level).sort(sort_function)) {
        if (index !== '/info') {
            if (target !== undefined && index === target[target.length - 1]) {
                target.pop()
                nested_header.appendChild(build_level(index, entry, target));
            } else {
                nested_header.appendChild(build_level(index, entry));
            }
        }
    }

    placeholder_dom.addEventListener('click', (event) => {
        on_level_click(event, level, nested_level_dom, nested_level_dom.parentNode.querySelector('div.header'));
    });

    nested_level_dom.appendChild(placeholder_dom)
    nested_level_dom.appendChild(nested_header)

    checkbox_block_other()
}

const on_level_click = function (event, level, nested_level_dom, current_level_dom) {
    document.getElementById('goto_input').value = level['/info'].path
    if (is_file(level)) {
        return
    }

    set_icon(nested_level_dom, current_level_dom);

    if (nested_level_dom.innerHTML === "") {
        build_nested_levels(level, nested_level_dom)
    } else {
        remove_all_children(nested_level_dom);
    }
}

const set_icon = function (nested_level_dom, current_level_dom) {
    const expand_button = current_level_dom.querySelector(`span > div.expand > img`);

    if (nested_level_dom.innerHTML === "") {
        expand_button.src = "folder_moins.png";
    } else {
        expand_button.src = "folder_plus.png";
    }
}

const is_file = function (level) {
    return level['/info'].type === 'file' || level['/info'].type === 'symlink'
}

const get_level_icon = function (level) {
    return {
        'file': null,
        'dir': 'folder_plus.png',
        'symlink': 'symlink.png'
    }[level['/info'].type]
}

const checkbox_click_event = function (event, path, type) {
    event.stopImmediatePropagation();
    event.stopPropagation();

    let list_to_use = exclude_list;

    if (type === "include") {
        list_to_use = include_list;
    }

    list_to_use[path] = event.target.checked;
    checkbox_block_other()
}

// On restic you cannot use --include and --exclude in the same command
const checkbox_block_other = function() {
    const count_included = Object.values(include_list).filter(Boolean).length;
    const count_excluded = Object.values(exclude_list).filter(Boolean).length;

    const exclusion_checkboxes = document.querySelectorAll('input[data-type="exclude"]');
    const inclusion_checkboxes = document.querySelectorAll('input[data-type="include"]');

    const disableExclusions = count_included > 0;
    const disableInclusions = count_excluded > 0 && count_included === 0;

    exclusion_checkboxes.forEach(item => {
        item.disabled = disableExclusions;
    });

    inclusion_checkboxes.forEach(item => {
        item.disabled = disableInclusions;
    });
};

const generate_extract_command = function () {
    let included_patterns = "";
    let excluded_patterns = "";

    Object.entries(include_list).forEach((item) => {
        if (item[1]) {
            included_patterns += ` --include "${item[0]}"`;
        }
    })

    Object.entries(exclude_list).forEach((item) => {
        if (item[1]) {
            excluded_patterns += ` --exclude "${item[0]}"`;
        }
    })

    prompt('Extract command', `${app_config.app.restic_executable_path} --repo "${app_config.repo[query_repo].url}" --password-file ".secrets/${query_repo}" restore "${metadata.short_id}" ${included_patterns}${excluded_patterns} --verbose=2 --target / --dry-run `);
}

const generate_export_tar_command = function () {
    let included_patterns = "";
    let excluded_patterns = "";

    Object.entries(include_list).forEach((item) => {
        if (item[1]) {
            included_patterns += ` "${item[0]}"`;
        }
    })

    Object.entries(exclude_list).forEach((item) => {
        if (item[1]) {
            excluded_patterns += ` --exclude "${item[0]}"`;
        }
    })

    prompt('Export command', `${app_config.app.restic_executable_path} restore ${query_repo}::${metadata.short_id} archive.tar${included_patterns}${excluded_patterns}`);
}

const build_level = function (index, level, target) {
    const level_data = get_data(level);
    const level_path = get_path(level);
    const is_level_file = is_file(level);

    const html_content_dom = document.createRange().createContextualFragment(template_method(index, level, target));
    const checkboxes = html_content_dom.querySelectorAll('input[type="checkbox"]');

    checkboxes.forEach((item) => {
        if (index === '/') {
            item.remove()
        } else {
            item.addEventListener('click', (event) => {
                checkbox_click_event(event, level_path, event.target.dataset.type);
            })
        }
    })


    const nested_level_dom = html_content_dom.querySelector('.nested_level');
    const header_dom_object = html_content_dom.querySelector(`div.header`);

    header_dom_object.addEventListener('click', (event) => {
        on_level_click(event, level, nested_level_dom, header_dom_object);
    });

    if (is_level_file) {
        return html_content_dom;
    }

    if (target !== undefined && target.length > 0) {
        set_icon(nested_level_dom, header_dom_object);
        build_nested_levels(level, nested_level_dom, target);
    }

    return html_content_dom;
}

const include_list = {};
const exclude_list = {};

let data;
let metadata;

const init_request = function () {
    set_sort_method()

    fetch(api_url)
        .then(function (response) {
            return response.json();
        }).then(function (response) {
        data = response.data
        metadata = response.metadata
        app_config = response.config
        build_treeview(data)
        init_dom_informations(metadata)
    })
}

const build_treeview = function (response, target) {
    const main_container_dom = document.getElementById('content');

    remove_all_children(main_container_dom);

    const root_level = build_level('/', response, target);
    main_container_dom.appendChild(root_level);

    if (target === undefined) {
        const nested_level_dom = main_container_dom.querySelector(`.nested_level`)
        set_icon(nested_level_dom, main_container_dom.querySelector(`div.header`));
        build_nested_levels(response, nested_level_dom, target);
    }
}

const set_sort_method = function () {
    const sorting_method = document.getElementById('sorting_method').value;
    sorting_reversed = document.getElementById('reverse_sorting').checked;

    if (sorting_method === 'added_size') {
        sort_function = added_size_sort
    } else if (sorting_method === 'removed_size') {
        sort_function = removed_size_sort;
    } else if (sorting_method === 'diff_size') {
        sort_function = diff_size_sort;
    } else if (sorting_method === 'name') {
        sort_function = alphabetical_sort;
    }
}

const change_sort_method = function () {
    set_sort_method();

    if (data) {
        build_treeview(data);
    }
}

const get_size_delta = function (changes_object, type) {
    let return_value;

    if (changes_object.type === 'added' && type === 'added') {
        return_value = changes_object.size;
    } else if (changes_object.type === 'removed' && type === 'removed') {
        return_value = changes_object.size;
    } else if (type === 'added') {
        return_value = changes_object.added;
    } else if (type === 'removed') {
        return_value = changes_object.removed;
    }

    if (return_value === undefined) {
        return_value = 0
    }

    return return_value;
}

const go_to_target = function (target) {
    const split_target = target.replace(/^\//, '').split('/');

    build_treeview(data, split_target.reverse());
    location.href = `#${target.replace(/\/$/, '').replace(/^\//, '')}`;
}

const goto_button_click = function (event) {
    const input_value = document.getElementById('goto_input').value;

    go_to_target(input_value)
}
