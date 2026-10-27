-- MOSQUERA Farm Logs — initial table design (DDL)
-- Target: MariaDB 10.4+ / MySQL 8, utf8mb4
-- Creates the farm, core (login tracking), and info tables.
-- Django's auth_* tables are created by `python manage.py migrate`.

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET NAMES utf8mb4 */;

-- --------------------------------------------------------

--
-- Table structure for table `farm_gardenarea`
--

CREATE TABLE `farm_gardenarea` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `name` varchar(120) NOT NULL,
  `kind` varchar(20) NOT NULL DEFAULT 'raised_bed',
  `rows` int(10) UNSIGNED NOT NULL DEFAULT 4 CHECK (`rows` >= 1),
  `cols` int(10) UNSIGNED NOT NULL DEFAULT 4 CHECK (`cols` >= 1),
  `description` longtext DEFAULT NULL,
  `created_at` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `farm_plant`
--

CREATE TABLE `farm_plant` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `area_id` bigint(20) DEFAULT NULL,
  `name` varchar(120) NOT NULL,
  `variety` varchar(120) DEFAULT NULL,
  `planting_date` date NOT NULL,
  `start_method` varchar(20) NOT NULL DEFAULT '' CHECK (`start_method` IN ('', 'direct', 'transplant')),
  `days_to_harvest` int(10) UNSIGNED NOT NULL DEFAULT 60 CHECK (`days_to_harvest` >= 1),
  `quantity` int(10) UNSIGNED NOT NULL DEFAULT 1 CHECK (`quantity` >= 1),
  `status` varchar(20) NOT NULL DEFAULT 'seedling',
  `water_every_days` int(10) UNSIGNED NOT NULL DEFAULT 2 CHECK (`water_every_days` >= 1),
  `fertilize_every_days` int(10) UNSIGNED NOT NULL DEFAULT 14 CHECK (`fertilize_every_days` >= 1),
  `pos_x` int(10) UNSIGNED NOT NULL DEFAULT 0,
  `pos_y` int(10) UNSIGNED NOT NULL DEFAULT 0,
  `notes` longtext DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `farm_reminder`
--

CREATE TABLE `farm_reminder` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `plant_id` bigint(20) NOT NULL,
  `kind` varchar(20) NOT NULL DEFAULT 'custom',
  `message` varchar(255) NOT NULL,
  `due_date` date NOT NULL,
  `is_done` tinyint(1) NOT NULL DEFAULT 0,
  `done_at` date DEFAULT NULL,
  `weather_paused` tinyint(1) NOT NULL DEFAULT 0,
  `postponed_from` date DEFAULT NULL,
  `created_at` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `farm_carelog`
--

CREATE TABLE `farm_carelog` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `plant_id` bigint(20) NOT NULL,
  `date` date NOT NULL,
  `category` varchar(20) NOT NULL DEFAULT 'note',
  `description` longtext NOT NULL,
  `photo` varchar(255) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `farm_dailycheck`
--

CREATE TABLE `farm_dailycheck` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `plant_id` bigint(20) NOT NULL,
  `date` date NOT NULL,
  `watered` tinyint(1) NOT NULL DEFAULT 0,
  `fertilized` tinyint(1) NOT NULL DEFAULT 0,
  `health` varchar(20) NOT NULL DEFAULT 'good',
  `height_cm` decimal(6,2) DEFAULT NULL,
  `notes` longtext DEFAULT NULL,
  `created_at` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `core_loginevent`
--

CREATE TABLE `core_loginevent` (
  `id` bigint(20) NOT NULL,
  `user_id` int(11) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `tblinfo`
--

CREATE TABLE `tblinfo` (
  `id` bigint(20) NOT NULL,
  `name` varchar(255) NOT NULL,
  `age` int(10) UNSIGNED NOT NULL CHECK (`age` BETWEEN 1 AND 150),
  `address` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Indexes for dumped tables
--

ALTER TABLE `farm_gardenarea`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_area_per_user` (`user_id`,`name`),
  ADD KEY `farm_gardenarea_user_id` (`user_id`);

ALTER TABLE `farm_plant`
  ADD PRIMARY KEY (`id`),
  ADD KEY `farm_plant_user_id` (`user_id`),
  ADD KEY `farm_plant_area_id` (`area_id`),
  ADD KEY `farm_plant_status` (`user_id`,`status`);

ALTER TABLE `farm_reminder`
  ADD PRIMARY KEY (`id`),
  ADD KEY `farm_reminder_due_date` (`due_date`),
  ADD KEY `farm_reminder_plant_done` (`plant_id`,`is_done`),
  ADD KEY `farm_reminder_user_id` (`user_id`);

ALTER TABLE `farm_carelog`
  ADD PRIMARY KEY (`id`),
  ADD KEY `farm_carelog_plant_date` (`plant_id`,`date`),
  ADD KEY `farm_carelog_user_id` (`user_id`);

ALTER TABLE `farm_dailycheck`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_check_per_plant_day` (`plant_id`,`date`),
  ADD KEY `farm_dailycheck_user_id` (`user_id`);

ALTER TABLE `core_loginevent`
  ADD PRIMARY KEY (`id`),
  ADD KEY `core_loginevent_created_at` (`created_at`),
  ADD KEY `core_loginevent_user_id` (`user_id`);

ALTER TABLE `tblinfo`
  ADD PRIMARY KEY (`id`),
  ADD KEY `tblinfo_user_id` (`user_id`);

-- --------------------------------------------------------

--
-- AUTO_INCREMENT for dumped tables
--

ALTER TABLE `farm_gardenarea` MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;
ALTER TABLE `farm_plant` MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;
ALTER TABLE `farm_reminder` MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;
ALTER TABLE `farm_carelog` MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;
ALTER TABLE `farm_dailycheck` MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;
ALTER TABLE `core_loginevent` MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;
ALTER TABLE `tblinfo` MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

-- --------------------------------------------------------

--
-- Constraints for dumped tables
--

ALTER TABLE `farm_gardenarea`
  ADD CONSTRAINT `farm_gardenarea_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE;

ALTER TABLE `farm_plant`
  ADD CONSTRAINT `farm_plant_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `farm_plant_area_id_fk` FOREIGN KEY (`area_id`) REFERENCES `farm_gardenarea` (`id`) ON DELETE SET NULL;

ALTER TABLE `farm_reminder`
  ADD CONSTRAINT `farm_reminder_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `farm_reminder_plant_id_fk` FOREIGN KEY (`plant_id`) REFERENCES `farm_plant` (`id`) ON DELETE CASCADE;

ALTER TABLE `farm_carelog`
  ADD CONSTRAINT `farm_carelog_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `farm_carelog_plant_id_fk` FOREIGN KEY (`plant_id`) REFERENCES `farm_plant` (`id`) ON DELETE CASCADE;

ALTER TABLE `farm_dailycheck`
  ADD CONSTRAINT `farm_dailycheck_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `farm_dailycheck_plant_id_fk` FOREIGN KEY (`plant_id`) REFERENCES `farm_plant` (`id`) ON DELETE CASCADE;

ALTER TABLE `core_loginevent`
  ADD CONSTRAINT `core_loginevent_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE;

ALTER TABLE `tblinfo`
  ADD CONSTRAINT `tblinfo_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE;

COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
