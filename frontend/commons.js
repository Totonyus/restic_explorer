const add_heading_sign = function (number) {
    let return_value = '';
    if (number < 0) {
        return_value = "-";
    } else if (number > 0) {
        return_value = "+";
    }

    return return_value
}

const current_date = new Date();
const get_linux_date_format = function (timestamp) {
    if (!timestamp) {
        return "";
    }

    const date = new Date(timestamp);

    const month_mapping = [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec'
    ]

    if (date.getFullYear() < current_date.getFullYear()) {
        return `${month_mapping[date.getMonth()]}&nbsp;${add_heading_space(date.getDate())}&nbsp;&nbsp;${date.getFullYear()}`;
    } else {
        return `${month_mapping[date.getMonth()]}&nbsp;${add_heading_space(date.getDate())}&nbsp;${add_heading_zero(date.getHours())}:${add_heading_zero(date.getMinutes())}`;
    }
}

const file_size = function (size) {
    const base = 1000;
    const conv_table = {
        'Po': size / (base ** 5),
        'To': size / (base ** 4),
        'Go': size / (base ** 3),
        'Mo': size / (base ** 2),
        'Ko': size / base,
        'o': size
    };

    let effective_unit;
    let effective_size;

    for (let conv in conv_table) {
        if (Math.abs(conv_table[conv]) >= 1) {
            effective_unit = conv;
            effective_size = conv_table[conv];

            return `${Math.abs(Math.round(effective_size * 100) / 100)}${effective_unit}`;
        }
    }

    return "";
}

const add_heading_zero = function (number) {
    return number < 10 ? `0${number}` : '' + number;
}

const add_heading_space = function (number) {
    return number < 10 ? `&nbsp;${number}` : '' + number;
}

