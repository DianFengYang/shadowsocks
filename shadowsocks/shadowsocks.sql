-- ---
-- Globals
-- ---

-- SET SQL_MODE="NO_AUTO_VALUE_ON_ZERO";
-- SET FOREIGN_KEY_CHECKS=0;

-- ---
-- Table 'users'
--
-- ---

DROP TABLE IF EXISTS `user`;

CREATE TABLE `user` (
  `id` INTEGER(11) NOT NULL AUTO_INCREMENT,
  `email` TEXT NOT NULL,
  `user_pass` TEXT NOT NULL,
  `port` INTEGER(11) NOT NULL,
  `passwd` TEXT NOT NULL,
  `t` BIGINT(20) NOT NULL DEFAULT 0,
  `d` BIGINT(20) NOT NULL DEFAULT 0,
  `u` BIGINT(20) NOT NULL DEFAULT 0,
  `enable` TINYINT(1) NOT NULL DEFAULT 0,
  `effective_date` INTEGER(11) NOT NULL DEFAULT 0,
  `expire_date` INTEGER(11) NOT NULL DEFAULT 0,
  `last_active_time` INTEGER(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
);

-- ---
-- Foreign Keys
-- ---


-- ---
-- Table Properties
-- ---

ALTER TABLE `user` ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;

-- ---
-- Test Data
-- ---

INSERT INTO `user` VALUES ('1', 'test1@test.com', '123456', '8382', 'asdfghjkl', '1024', '0', '0', '1', '0', '0', '0');
INSERT INTO `user` VALUES ('2', 'test2@test.com', '123456', '8381', 'qwertyuiop', '1073741824', '0', '0', '1', '0', '0', '0');
INSERT INTO `user` VALUES ('3', 'test3@test.com', '123456', '50002', 'zxcvbnm', '10240', '0', '0', '0', '0', '0', '0');