let api_url, repo_template_method, snapshot_template_method, report_type, app_config

const init_core = function (object) {
    repo_template_method = object.repo_template_method;
    snapshot_template_method = object.snapshot_template_method;
    get_path = object.get_path;
    get_data = object.get_data;
    report_type = object.report_type;
    api_url = `/api/${object.api_url}`;
}


const build_repo_list = function(repo_list){
    const main_container_dom = document.getElementById('content');
    remove_all_children(main_container_dom);

    for (let [repo_name, repo] of Object.entries(repo_list)) {
        const repo_html_content_dom = document.createRange().createContextualFragment(repo_template_method(repo_name, repo));
        const repo_snapshots_containers = repo_html_content_dom.querySelector('.repo_snapshots_container')

        const repo_name_dom = repo_html_content_dom.querySelector('.repo_name')
        const container = repo_html_content_dom.getElementById(`snapshot_container_${repo_name}`)
        const updown_indicator = repo_html_content_dom.querySelector('.updown_indicator>img')

        repo_name_dom.addEventListener('click', ()=>{
            let state = toggle_class(container, 'hidden')
            updown_indicator.src = state === 'added' ? 'down.png' : 'up.png'
        })

        const mount_button = repo_html_content_dom.querySelector('.mount_button');
        mount_button.addEventListener('click', (e) => {
            prompt('Mount command',
                `${app_config.app.restic_executable_path} --repo "${repo.params.url}" --password-file ".secrets/${repo_name}" mount "${repo.params.backup_mountpoint}" `);
        })

        if (repo.snapshots != null) {
            for (let [snapshot_index, snapshot] of Object.entries(repo.snapshots.reverse())) {
                const snapshot_html_content_dom = document.createRange().createContextualFragment(snapshot_template_method(snapshot));

                const explore_button = snapshot_html_content_dom.querySelector('.explore_button')
                explore_button.addEventListener('click', (e) => {
                    window.open(`/ui/list.html?repo=${repo_name}&snapshot1=${snapshot.short_id}`)
                })

                repo_snapshots_containers.appendChild(snapshot_html_content_dom)

            }
        }else{
            const snapshot_html_content_dom = document.createRange().createContextualFragment(`<div class='no_snapshot_available'>An error occured : ${repo.params.error.message}</div>`);
            repo_snapshots_containers.appendChild(snapshot_html_content_dom)

        }
        main_container_dom.appendChild(repo_html_content_dom);
    }

    const refresh_cache_button = document.createRange().createContextualFragment(`<div id="refresh_cache_button" class="button refresh_cache_button">Refresh cache</div>`)
    const button = refresh_cache_button.getElementById('refresh_cache_button')
    button.addEventListener('click', ()=>{
        replace_loading_animation()
        init_request('?force_refresh=true')
    })

    main_container_dom.appendChild(refresh_cache_button)
}

const init_request = function (param = '') {
    fetch(api_url + param)
        .then(function (response) {
            return response.json();
        }).then(function (response) {
        data = response.data
        app_config = response.config
        build_repo_list(data)
    })
}

const remove_all_children = function (dom_object) {
    while (dom_object.firstChild) {
        dom_object.firstChild.remove();
    }
}

const replace_loading_animation = function() {
    const content_dom_element = document.getElementById('content')
    remove_all_children(content_dom_element)

    content_dom_element.innerHTML= `
        <div id="loading_animation">
            <div class="lds-ellipsis">
                <div></div>
                <div></div>
                <div></div>
                <div></div>
            </div>
        </div>`
}

const toggle_class = function (element, classe) {
    if (element.classList.contains(classe)) {
        element.classList.remove(classe)
        return 'removed'
    } else {
        element.classList.add(classe)
        return 'added'
    }

}